#!/usr/bin/env python3

import dataset
import pydicom
import os
import pathlib
from collections import defaultdict
from tqdm import tqdm
from .syd_helpers import *
from .syd_db import *
from shutil import copyfile

# -----------------------------------------------------------------------------
def create_dicom_serie_table(db):
    '''
    Create the DicomSerie table
    '''

    # other fields ?
    # manufacturer manufacturer_model_name software_version
    # pixel_scale pixel_offset window_center window_width radionuclide_name
    # counts_accumulated actual_frame_duration_in_msec
    # number_of_frames_in_rotation number_of_rotations table_traverse_in_mm
    # table_height_in_mm rotation_angle real_world_value_slope
    # real_world_value_intercept

    # WARNING series_uid is not unique ! Thw DicomSerie may be different with
    # the same DicomSerie

    # create DicomSerie table
    q = 'CREATE TABLE DicomSerie (\
    id INTEGER PRIMARY KEY NOT NULL,\
    patient_id INTEGER,\
    injection_id INTEGER,\
    series_uid INTEGER NOT NULL,\
    sop_uid INTEGER NOT NULL UNIQUE,\
    study_uid INTEGER NOT NULL,\
    frame_of_reference_uid INTEGER,\
    modality TEXT,\
    series_description TEXT,\
    study_description TEXT,\
    study_name TEXT,\
    dataset_name TEXT,\
    folder TEXT,\
    FOREIGN KEY (patient_id) REFERENCES Patient (id) on delete cascade,\
    FOREIGN KEY (injection_id) REFERENCES Injection (id) on delete cascade\
    )'
    result = db.query(q)
    dicom_serie_table = db['DicomSerie']
    dicom_serie_table.create_column('acquisition_date', db.types.datetime)
    dicom_serie_table.create_column('reconstruction_date', db.types.datetime)


# -----------------------------------------------------------------------------
def create_dicom_file_table(db):
    '''
    Create the DicomFile table
    '''

    # create DicomFile table
    q = 'CREATE TABLE DicomFile (\
    id INTEGER PRIMARY KEY NOT NULL,\
    file_id INTEGER NOT NULL UNIQUE,\
    dicom_serie_id INTEGER NOT NULL,\
    sop_uid INTEGER NOT NULL UNIQUE,\
    instance_number INTEGER NOT NULL,\
    FOREIGN KEY (file_id) REFERENCES File (id) on delete cascade,\
    FOREIGN KEY (dicom_serie_id) REFERENCES DicomSerie (id) on delete cascade\
    )'
    result = db.query(q)

    # define trigger
    con = db.engine.connect()
    cur = con.connection.cursor()
    #  SELECT dicomfile_on_delete(OLD.file_id);
    cur.execute("CREATE TRIGGER on_dicomfile_delete AFTER DELETE ON DicomFile BEGIN\
    DELETE FROM File WHERE id=OLD.file_id;\
    END;")
    con.close()


# -----------------------------------------------------------------------------
def dicomfile_on_delete(x):
    # NOT USED (keep here for example)
    print('on delete', x)


# -----------------------------------------------------------------------------
def set_dicom_triggers(db):
    #con = db.engine.connect()
    #con.connection.create_function("dicomfile_on_delete", 1, dicomfile_on_delete)
    # Do nothing (no function needed)
    pass

# -----------------------------------------------------------------------------
def insert_dicom(db, folder, patient_id=0):
    '''
    Search for Dicom Series in the folder and insert in the database.

    Options FIXME
    - for each NM serie -> associate injection/patient
    - what about several series ?
    - recursive
    - option: copy or link files in the db image folder
    - what kind of tags stored in the tables ?? how stored ?
    '''

    # get all the files (recursively)
    files = list(pathlib.Path(folder).rglob("*"))
    print('Found {} files/folders in {}'.format(len(files), folder))

    # read all dicom dataset to get the SeriesInstanceUID
    # store the sid, the filename and the dicom dataset
    dicoms = []
    pbar = tqdm(total=len(files), leave=False)
    for f in files:
        f = str(f)
        # ignore if this is a folder
        if (os.path.isdir(f)): continue
        # try to read the dicom file
        try:
            ds = pydicom.read_file(f)
            try:
                sid = ds.data_element("SeriesInstanceUID").value
                sopid = ds.data_element("SOPInstanceUID").value
                modality = ds.Modality
            except:
                tqdm.write('Ignoring {}: cannot find SeriesInstanceUID'.format(f))
            # ignore unmanaged modality
            if (modality == 'CT' or modality == 'PT' or modality == 'NM' or modality == 'OT'):
                if (modality == 'CT'):
                    s = {'sid':sid, 'f':f, 'ds': ds}
                else:
                    s = {'sid':sopid, 'f':f, 'ds': ds}
                dicoms.append(s)
            else:
                tqdm.write('Ignoring {}: modality is {}'.format(f,modality))
        except:
            tqdm.write('Ignoring {}: (not a dicom)'.format(f))
        # update progress bar
        pbar.update(1)
    pbar.close()

    # find all series, group corresponding files and dataset
    series = defaultdict(list)
    for d in dicoms:
        sid = d['sid']
        #sop = d['sopid']
        if sid in series:
            a = series[sid]
            a['f'].append(d['f'])
            a['ds'].append(d['ds'])
        else:
            series[sid] = { 'f':[d['f']], 'ds':[d['ds']]}

    # create series
    print('Found {} Dicom Series'.format(len(series)))
    dicom_series = []
    for k,v in series.items():
        ds = insert_dicom_serie(db, v['f'], v['ds'], patient_id)
        dicom_series.append(ds)

    return dicom_series

# -----------------------------------------------------------------------------
def insert_dicom_serie(db, filenames, dicom_datasets, patient_id):
    '''
    Insert one dicom serie, with all associated files
    If patient_id is 0, try to guess
    Try to associate one injection, only if only one exist for this patient.
    '''

    # consider only the first dataset
    ds = dicom_datasets[0]
    sid = ds.data_element('SeriesInstanceUID').value

    # check if this series already exist (only for CT)
    if ds.Modality == 'CT':
        dicom_serie = syd.find_one(db['DicomSerie'], series_uid=sid)
        if dicom_serie is not None:
            print('The Dicom Serie already exists in the db, ignoring {} ({} files)'
                  .format(filenames[0], len(filenames)))
            return
    else:
        # for other image check SOP, assume a single image per DicomSeries
        sid = ds.data_element('SOPInstanceUID').value
        dicom_serie = syd.find_one(db['DicomSerie'], sop_uid=sid)
        if dicom_serie is not None:
            print('The Dicom Serie (same SOP) already exists in the db, ignoring {} ({} files)'
                  .format(filenames[0], len(filenames)))
            return

    # get patient_id
    patient = None
    if (patient_id == 0):
        patient = guess_patient_from_dicom(db, ds)
        if (patient != None):
            patient_id = patient['id']

    # guess fail ?
    if (patient_id == 0):
        print('The dicom serie {} is ignored'.format(sid))
        print('In file: {}'.format(filenames[0]))
        return

    # check if patient exist
    if patient is None:
        print('Error, cannor find the patient with id {}'.format(patient_id))
        print('The dicom serie {} is ignored'.format(sid))
        return

    # get date
    try:
        acquisition_date = ds.AcquisitionDate
        acquisition_time = ds.AcquisitionTime
    except:
        acquisition_date = ds.InstanceCreationDate
        acquisition_time = ds.InstanceCreationTime
    acquisition_date = dcm_str_to_date(acquisition_date+' '+acquisition_time)

    try:
        reconstruction_date = ds.ContentDate
        reconstruction_time = ds.ContentTime
    except:
        reconstruction_date = ds.InstanceCreationDate
        reconstruction_time = ds.InstanceCreationTime
    reconstruction_date = dcm_str_to_date(reconstruction_date+' '+reconstruction_time)

    # get tag values that are bytes, not string
    try:
        study_name = ds[0x0009,0x1010].value.decode("utf-8")
    except:
        study_name = ''
    try:
        dataset_name = ds[0x0011, 0x1012].value.decode("utf-8")
    except:
        dataset_name = ''

    # guess injection if NM
    injection_id = None
    injection = None
    inj_txt = ''
    if ds.Modality != 'CT': ## FIXME -> not really.
        inj_txt = ' (no injection found)'
        injection = guess_injection_from_dicom(db, ds, patient)
        if injection != None:
            injection_id = injection['id']
            inj_txt = '(injection {})'.format(injection['id'])

    # build folder
    pname = syd.find_one(db['Patient'], id=patient_id)['name']
    date = acquisition_date.strftime('%Y-%m-%d')
    modality = ds.Modality
    folder = build_folder(db, pname, date, modality)
    folder = os.path.join(folder, 'dicom')

    # get values that may be none
    try:
        frame_of_reference_uid = ds.FrameOfReferenceUID
    except:
        frame_of_reference_uid = None

    # build info
    info = {
        'patient_id': patient_id,
        'injection_id': injection_id,
        'series_uid': ds.SeriesInstanceUID,
        'sop_uid': ds.data_element("SOPInstanceUID").value,
        'study_uid':  ds.StudyInstanceUID,
        'frame_of_reference_uid':  frame_of_reference_uid,
        'modality': modality,
        'series_description': ds.SeriesDescription,
        'study_description': ds.StudyDescription,
        'study_name': study_name,
        'dataset_name': dataset_name,
        'acquisition_date': acquisition_date,
        'reconstruction_date': reconstruction_date,
        'folder': folder
    }

    # insert the dicom serie
    dicom_serie = syd.insert_one(db['DicomSerie'], info)

    # create DicomFile and File
    dicom_file_info = []
    file_info = []
    i=0
    for f in filenames:
        ds = dicom_datasets[i]
        sop_uid = ds[0x0008, 0x0018].value # SOPInstanceUID
        df = syd.find_one(db['DicomFile'], sop_uid=sop_uid)
        if df is not None:
            print('Warning, a file with same sop_uid already exist, ignoring {}'.format(f))
            continue
        df, fi = create_dicom_file_info(db, modality, sid, folder, f, ds)
        if df is not None:
            dicom_file_info.append(df)
            file_info.append(fi)
        i = i+1

    # insert file
    files = syd.insert(db['File'], file_info)

    # change file_id in dicom_file
    i=0
    for d,f in zip(dicom_file_info, files):
        d['file_id'] = f['id']
    syd.insert(db['DicomFile'], dicom_file_info)

    # copy file
    for df, f in zip(file_info, filenames):
        src = f
        dst_folder = os.path.join(db.absolute_data_folder, df['folder'])
        dst = os.path.join(dst_folder, df['filename'])
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        #if os.path.exists(dst): FIXME overwrite ?
        copyfile(src, dst)

    # final verbose
    print('A new DicomSerie have been inserted ({} {} {} {} {}), with {} file(s) {}'.
          format(patient['name'],
                 dicom_serie['id'],
                 dicom_serie['modality'],
                 dicom_serie['acquisition_date'],
                 dicom_serie['dataset_name'],
                 len(dicom_file_info), inj_txt))

    return dicom_serie['id']

# -----------------------------------------------------------------------------
def guess_patient_from_dicom(db, ds):
    '''
    Try to guess the patient if from the dicom dataset using dicom_patient_id
    '''

    pid = ds.data_element('PatientID').value
    patients = db['Patient'].all()

    # look for dicom_id FIXME -> to change with a ad-hoc fct for vector data
    found = []
    for p in patients:
        ids = p['dicom_id']
        ids = ids.split(',')
        for tid in ids:
            if (tid == pid):
                found.append(p)

    # ----> FIXME to change with something like ?
    # table.find(db['Patient'].table.columns.dicom_id like tid)

    if (len(found) == 0):
        print('Cannot guess patient with PatientID {}'.format(pid))
        return None
    if (len(found) > 1):
        print('Several patients found with dicomID = {}, bug !?'.format(pid))
        return None

    return found[0]


# -----------------------------------------------------------------------------
def guess_injection_from_dicom(db, ds, patient):
    '''
    Try to guess the injection
    '''

    injections = syd.find(db['Injection'], patient_id=patient['id'])
    i = 0
    injection = None
    for inj in injections:
        if (i == 0):
            injection = inj
        else:
            injection = None
        i = i+1
    return injection


# -----------------------------------------------------------------------------
def create_dicom_file_info(db, modality, sid, folder, f, ds):
    '''
    Create dico with DicomFile and File information to be inserted
    '''

    if modality == 'CT':
        dicom_serie = syd.find_one(db['DicomSerie'], series_uid=sid)
    else:
        dicom_serie = syd.find_one(db['DicomSerie'], sop_uid=sid)

    dicom_file_info = {
        'dicom_serie_id': dicom_serie['id'],
        'sop_uid': ds[0x0008, 0x0018].value, # SOPInstanceUID
        'instance_number': ds.InstanceNumber
    }

    # filename = basename
    filename = os.path.basename(f)

    file_info = {
        'filename': filename,
        'folder': folder,
        #'md5': md5 # later
    }

    return dicom_file_info, file_info


# -----------------------------------------------------------------------------
def get_dicom_serie_files(db, dicom_serie):
    '''
    Return the list of files associated with the dicom_serie
    '''

    # get all dicom files
    dicom_files = syd.find(db['DicomFile'], dicom_serie_id=dicom_serie['id'])

    # get all associated id of the files
    fids = []
    for df in dicom_files:
        fids.append(df['file_id'])

    # find files
    #res = db['File'].find(id=fids)
    res = syd.find(db['File'], id=fids)
    files = []
    for r in res:
        files.append(r)
    return files
