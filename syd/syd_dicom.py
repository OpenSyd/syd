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

    # create DicomSerie table
    q = 'CREATE TABLE DicomSerie (\
    id INTEGER PRIMARY KEY NOT NULL,\
    patient_id INTEGER,\
    injection_id INTEGER,\
    series_uid INTEGER NOT NULL UNIQUE,\
    study_uid INTEGER NOT NULL,\
    frame_of_reference_uid INTEGER NOT NULL,\
    modality TEXT,\
    series_description TEXT,\
    study_description TEXT,\
    study_name TEXT,\
    dataset_name TEXT,\
    FOREIGN KEY(patient_id) REFERENCES Patient(id),\
    FOREIGN KEY(injection_id) REFERENCES Injection(id)\
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
    dicom_serie_id INTEGER NOT NULL,\
    file_id INTEGER NOT NULL UNIQUE,\
    sop_uid INTEGER NOT NULL UNIQUE,\
    instance_number INTEGER NOT NULL,\
    FOREIGN KEY(dicom_serie_id) REFERENCES DicomSerie(id),\
    FOREIGN KEY(file_id) REFERENCES File(id)\
    )'
    result = db.query(q)


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
            except:
                tqdm.write('Ignoring {}: cannot find SeriesInstanceUID'.format(f))
            # ignore unmanaged modality
            modality = ds.Modality
            if (modality == 'CT' or modality == 'PT' or modality == 'NM'):
                s = {'sid':sid, 'f':f, 'ds': ds}
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
        if sid in series:
            a = series[sid]
            a['f'].append(d['f'])
            a['ds'].append(d['ds'])
        else:
            series[sid] = { 'f':[d['f']], 'ds':[d['ds']]}

    # create series
    print('Found {} Dicom Series'.format(len(series)))
    ids = []
    for k,v in series.items():
        id = insert_dicom_serie(db, v['f'], v['ds'], patient_id)
        ids.append(id)

    return ids

# -----------------------------------------------------------------------------
def insert_dicom_serie(db, files, dicom_datasets, patient_id):
    '''
    Insert one dicom serie, with all associated files
    If patient_id is 0, try to guess
    Try to associate one injection, only if only one exist for this patient.
    '''

    # consider only the first dataset
    ds = dicom_datasets[0]
    sid = ds.data_element('SeriesInstanceUID').value

    # check if this series already exist
    dicom_serie = db['DicomSerie'].find_one(series_uid=sid)
    if dicom_serie is not None:
        print('The Dicom Serie already exists in the db, ignoring {} ({} files)'
              .format(files[0], len(files)))
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
        print('In file: {}'.format(files[0]))
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
    if ds.Modality == 'PT' or ds.Modality == 'NM':
        inj_txt = ' (no injection found)'
        injection = guess_injection_from_dicom(db, ds, patient)
        if injection != None:
            injection_id = injection['id']
            inj_txt = '(injection {})'.format(injection['id'])

    # build info
    info = {
        'patient_id': patient_id,
        'injection_id': injection_id,
        'series_uid': ds.SeriesInstanceUID,
        'study_uid':  ds.StudyInstanceUID,
        'frame_of_reference_uid':  ds.FrameOfReferenceUID,
        'modality': ds.Modality,
        'series_description': ds.SeriesDescription,
        'study_description': ds.StudyDescription,
        'study_name': study_name,
        'dataset_name': dataset_name,
        'acquisition_date': acquisition_date,
        'reconstruction_date': reconstruction_date,
    }

    # insert the dicom serie
    i = db['DicomSerie'].insert(info)
    dicom_serie = db['DicomSerie'].find_one(id=i)

    # create DicomFile and File
    dicom_file_info = []
    file_info = []
    i=0
    for f in files:
        ds = dicom_datasets[i]
        sop_uid = ds[0x0008, 0x0018].value # SOPInstanceUID
        df = db['DicomFile'].find_one(sop_uid=sop_uid)
        if df is not None:
            print('Warning, a file with same sop_uid already exist, ignoring {}'.format(f))
            continue
        df, fi = create_dicom_file_info(db, sid, f, ds)
        if df is not None:
            dicom_file_info.append(df)
            file_info.append(fi)
        i = i+1

    # insert file
    ids = syd.insert(db['File'], file_info)

    # change file_id in dicom_file
    i=0
    for d,i in zip(dicom_file_info, ids):
        d['file_id'] = i
    syd.insert(db['DicomFile'], dicom_file_info)

    # copy file
    for df, f in zip(file_info, files):
        src = f
        dst = os.path.join(df['path'], df['filename'])
        if not os.path.exists(df['path']):
            os.makedirs(df['path'])
        #if os.path.exists(dst): FIXME overwrite ?
        copyfile(src, dst)

    # final verbose
    print('A new DicomSerie have been inserted ({} {} {}), with {} files {}'.
          format(patient['name'],
                 dicom_serie['modality'],
                 dicom_serie['acquisition_date'],
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

    injections = db['Injection'].find(patient_id=patient['id'])
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
def create_dicom_file_info(db, sid, f, ds):
    '''
    Create dico with DicomFile and File information to be inserted
    '''

    dicom_serie = db['DicomSerie'].find_one(series_uid=sid)
    dicom_file_info = {
        'dicom_serie_id': dicom_serie['id'],
        'sop_uid': ds[0x0008, 0x0018].value, # SOPInstanceUID
        'instance_number': ds.InstanceNumber
    }

    # folder : patient_name/date/modality
    pname = db['Patient'].find_one(id=dicom_serie['patient_id'])['name']
    date = dicom_serie['acquisition_date'].strftime('%Y-%m-%d')
    modality = dicom_serie['modality']
    info = db['Info'].find_one(id=1)
    path = os.path.join(info['image_folder'],pname)
    path = os.path.join(path,date)
    path = os.path.join(path,modality)

    # filename = basename
    filename = os.path.basename(f)

    file_info = {
        'filename': filename,
        'path': path,
        #'md5': md5 # later
    }

    return dicom_file_info, file_info

