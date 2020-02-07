#!/usr/bin/env python3

import dataset
import pydicom
import numpy as np
import os
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm
from .syd_helpers import *
from .syd_db import *
from shutil import copyfile
from datetime import datetime
from datetime import timedelta

'''
DICOM Module
------------

Tables
------
- DicomStudy   : patient_id study_uid study_description study_name
- DicomSeries  : dicom_study_id injection_id series_uid series_description
                 modality frame_of_reference_uid dataset_name
                 image_size image_spacing
                 folder
- DicomFile    : file_id sop_uid dicom_serie_id instance_number



Functions
---------
- insert_dicom_from_folder
- insert_dicom_from_file
- insert_dicom_series_from_dataset(db, ds, patient)
- insert_dicom_study_from_dataset(db, ds, patient)
- insert_dicom_file_from_dataset(db, ds, filename, dicom_series)

- build_dicom_series_folder(db, dicom_series)
- guess_or_create_patient(db, ds)
- get_dicom_image_info(ds)

- guess_or_create_injection(db, ds, dicom_series)
- search_injection_from_info(db, dicom_study, rad_info)
- search_injection(db, ds, dicom_study, dicom_series)
- new_injection(db, dicom_study, rad_info)


Verbose policy
--------------

- print when a file is ignored
- print when a file is inserted


Principles
---------

Always ignore if a uid already present in the DB. To update, delete the elements first.

Files are inserted and copied successively, not in batch. Maybe slower. But allow cancel.

Patient are created according to Dicom tag 'PatientID'. If it is null
or void, will still create a patient. Alternatively, patient may be
indicated in the function call.

Injection: search in the Dicom some tag, if found, try to match with
existing injection or create a new one. If no information in the
dicom, try to match with injection (patient and date), or ignore.

'''

# -----------------------------------------------------------------------------
def create_dicom_study_table(db):
    '''
    Create the DicomStudy table
    '''

    q = 'CREATE TABLE DicomStudy (\
    id INTEGER PRIMARY KEY NOT NULL,\
    patient_id INTEGER,\
    study_uid TEXT NOT NULL,\
    study_description TEXT,\
    study_name TEXT,\
    FOREIGN KEY (patient_id) REFERENCES Patient (id) on delete cascade\
    )'
    result = db.query(q)


# -----------------------------------------------------------------------------
def create_dicom_series_table(db):
    '''
    Create the DicomSeries table
    '''

    q = 'CREATE TABLE DicomSeries (\
    id INTEGER PRIMARY KEY NOT NULL,\
    dicom_study_id INTEGER NOT NULL,\
    injection_id INTEGER,\
    series_uid INTEGER NOT NULL,\
    dataset_uid INTEGER,\
    series_description TEXT,\
    modality TEXT,\
    frame_of_reference_uid INTEGER,\
    dataset_name TEXT,\
    image_size TEXT,\
    image_spacing TEXT,\
    folder TEXT,\
    image_comments TEXT,\
    FOREIGN KEY (dicom_study_id) REFERENCES DicomStudy (id) on delete cascade,\
    FOREIGN KEY (injection_id) REFERENCES Injection (id) on delete cascade\
    )'
    result = db.query(q)
    dicom_serie_table = db['DicomSeries']
    dicom_serie_table.create_column('acquisition_date', db.types.datetime)
    dicom_serie_table.create_column('reconstruction_date', db.types.datetime)


# -----------------------------------------------------------------------------
def create_dicom_file_table(db):
    '''
    Create the DicomFile table.

    '''

    # create DicomFile table
    q = 'CREATE TABLE DicomFile (\
    id INTEGER PRIMARY KEY NOT NULL,\
    file_id INTEGER NOT NULL UNIQUE,\
    dicom_series_id INTEGER NOT NULL,\
    sop_uid INTEGER NOT NULL UNIQUE,\
    instance_number INTEGER,\
    FOREIGN KEY (file_id) REFERENCES File (id) on delete cascade,\
    FOREIGN KEY (dicom_series_id) REFERENCES DicomSeries (id) on delete cascade\
    )'
    result = db.query(q)

    # define trigger
    con = db.engine.connect()
    cur = con.connection.cursor()
    cur.execute('CREATE TRIGGER on_dicomfile_delete AFTER DELETE ON DicomFile\
    BEGIN\
    DELETE FROM File WHERE id = OLD.file_id;\
    END;')
    con.close()

    # if dicom trigger --> add this line before DELETE FROM File
    #     SELECT on_dicomfile_delete(OLD.id);\


# -----------------------------------------------------------------------------
def on_dicomfile_delete(db, x):
    # NOT really used. Kept here for example and display delete message
    print('Delete DicomFile ', x)


# -----------------------------------------------------------------------------
def set_dicom_triggers(db):
    con = db.engine.connect()
    def t(x):
        on_dicomfile_delete(db, x)

    con.connection.create_function("on_dicomfile_delete", 1, t)


# -----------------------------------------------------------------------------
def insert_dicom_from_folder(db, folder, patient):
    '''
    New insert dicom from folder
    '''

    # get all the files (recursively)
    files = list(Path(folder).rglob("*"))
    tqdm.write('Found {} files/folders in {}'.format(len(files), folder))

    pbar = tqdm(total=len(files), leave=False)
    dicoms = []
    future_dicom_files = []
    for f in files:
        f = str(f)
        # ignore if this is a folder
        if (os.path.isdir(f)): continue
        # read the dicom file
        d = insert_dicom_from_file(db, f, patient, future_dicom_files)
        if d != {}:
            dicoms.append(d)
        # update progress bar
        pbar.update(1)

    # end pbar
    pbar.close()

    # maybe some remaining future files should be inserted
    dicom_files = insert_future_dicom_files(db, future_dicom_files)

    tqdm.write('Insertion of {} DICOM files.'.format(len(dicoms)))


# -----------------------------------------------------------------------------
def insert_dicom_from_file(db, filename, patient, future_dicom_files=[]):
    '''
    Insert or update a dicom from a filename
    '''

    # read the file
    try:
        ds = pydicom.read_file(filename)
    except:
        tqdm.write('Ignoring {}: not a dicom'.format(Path(filename).name))
        return {}

    # read study, series, instance
    try:
        sop_uid = ds.data_element("SOPInstanceUID").value
    except:
        tqdm.write('Ignoring {}: cannot read UIDs'.format(filename))
        return {}

    # check if this file already exist in the db
    dicom_file = syd.find_one(db['DicomFile'], sop_uid=sop_uid)

    if dicom_file is not None:
        tqdm.write('Ignoring {}: Dicom SOP Instance already in the db'.format(Path(filename).name))
        return {}

    # check in future
    for f in future_dicom_files:
        if sop_uid == f.dicom_file.sop_uid:
            tqdm.write('Ignoring {}: Dicom SOP Instance already planned'.format(Path(filename).name))
            return {}

    # retrieve series or create if not exist
    try:
        series_uid = ds.data_element("SeriesInstanceUID").value
    except:
        tqdm.write('Ignoring {}: Dicom SOP Instance does not exist'.format(Path(filename).name))
        return {}
    try:
        number_of_frames = ds[0x0028, 0x0008].value
        volume = True
    except:
        volume = False

    if volume:
        dicom_series = None
    else:
        dicom_series = syd.find_one(db['DicomSeries'], series_uid=series_uid)

    if dicom_series is None:
        dicom_series = insert_dicom_series_from_dataset(db, ds, patient)
        dicom_series = syd.insert_one(db['DicomSeries'], dicom_series)
        dicom_series.folder = os.path.join(dicom_series.folder, str(dicom_series.id))
        syd.update_one(db['DicomSeries'], dicom_series)
        tqdm.write('Insert new DicomSeries {}'.format(dicom_series))

        # Insert previous files
        dd = insert_future_dicom_files(db, future_dicom_files)
        if len(future_dicom_files) == 1:
            tqdm.write(f'Insert DicomFile {future_dicom_files[0].dicom_file}')
        if len(future_dicom_files) > 1:
            tqdm.write(f'Insert {len(future_dicom_files)} DicomFiles')

        # delete future_dicom_files
        future_dicom_files[:] = []

    # update dicom file
    dicom_file = insert_dicom_file_from_dataset(db, ds, filename, dicom_series, future_dicom_files)
    if len(future_dicom_files) >1:
        tqdm.write(f'DicomFile {dicom_file.instance_number} detected (will be inserted later)')


# -----------------------------------------------------------------------------
def insert_dicom_series_from_dataset(db, ds, patient):

    # retrieve study or create if not exist
    study_uid = ds.data_element("StudyInstanceUID").value
    dicom_study = syd.find_one(db['DicomStudy'], study_uid=study_uid)
    if dicom_study is None:
        dicom_study = insert_dicom_study_from_dataset(db, ds, patient)
        dicom_study = syd.insert_one(db['DicomStudy'], dicom_study)
        tqdm.write('Insert new DicomStudy {}'.format(dicom_study))

    # id INTEGER PRIMARY KEY NOT NULL,\
        # injection_id INTEGER,\
        # image_size TEXT,\
        # image_spacing TEXT,\
        # folder TEXT,\
        # dicom_serie_table.create_column('acquisition_date', db.types.datetime)
    # dicom_serie_table.create_column('reconstruction_date', db.types.datetime)

    dicom_series = Box()
    dicom_series.dicom_study_id = dicom_study.id
    dicom_series.series_uid = ds.data_element("SeriesInstanceUID").value

    try:
        dicom_series.series_description = ds.data_element("SeriesDescription").value
    except:
        dicom_series.series_description = ''

    try:
        dicom_series.modality = ds.Modality
    except:
        dicom_series.modality = ''

    try:
        dicom_series.frame_of_reference_uid = ds.FrameOfReferenceUID
    except:
        dicom_series.frame_of_reference_uid = ''

    try:
        dicom_series.dataset_uid = ds[0x0009,0x101e].value
    except:
        dicom_series.dataset_uid = ''

    # dataset_name
    dicom_series.dataset_name = ''
    try:
        dicom_series.dataset_name = ds[0x0011, 0x1012].value # .decode("utf-8")
    except:
        pass
    a = dicom_series.dataset_name
    if isinstance(a, pydicom.multival.MultiValue):
        s = ''
        for v in a:
            s += v+' '
            dicom_series.dataset_name = s

    # image_comments
    dicom_series.image_comments = ''
    try:
        dicom_series.image_comments = ds[0x0020, 0x4000].value + ' '
    except:
        pass
    try:
        for rad in ds[0x0054, 0x0012]:
          dicom_series.image_comments += rad[0x0054, 0x0018].value + ' '
    except:
        pass

    # dates
    try:
        acquisition_date = ds.AcquisitionDate
        acquisition_time = ds.AcquisitionTime
    except:
        try:
            acquisition_date = ds.InstanceCreationDate
            acquisition_time = ds.InstanceCreationTime
        except:
            acquisition_date = ds.StructureSetDate
            acquisition_time = ds.StructureSetTime

    try:
        reconstruction_date = ds.ContentDate
        reconstruction_time = ds.ContentTime
    except:
        reconstruction_date = acquisition_date
        reconstruction_time = acquisition_time

    acquisition_date = dcm_str_to_date(acquisition_date+' '+acquisition_time)

    if len(reconstruction_date) < 8 or len(reconstruction_time) < 6:
        reconstruction_date = acquisition_date
    else:
        reconstruction_date = dcm_str_to_date(reconstruction_date+' '+reconstruction_time)

    dicom_series.acquisition_date = acquisition_date
    dicom_series.reconstruction_date = reconstruction_date

    # folder
    dicom_series.folder = build_dicom_series_folder(db, dicom_series)

    # image size
    image_size, image_spacing = get_dicom_image_info(ds)
    dicom_series.image_size = image_size
    dicom_series.image_spacing = image_spacing

    # try to guess injection (later)
    inj = guess_or_create_injection(db, ds, dicom_study, dicom_series) # FIXME do it later
    if inj:
        dicom_series.injection_id = inj.id

    return dicom_series

# -----------------------------------------------------------------------------
def build_dicom_series_folder(db, dicom_series):
    dicom_study = syd.find_one(db['DicomStudy'], id=dicom_series.dicom_study_id)
    patient_id = dicom_study.patient_id
    pname = syd.find_one(db['Patient'], id=patient_id).name
    date = dicom_series.acquisition_date.strftime('%Y-%m-%d')
    modality = dicom_series.modality
    folder = os.path.join(pname, date)
    folder = os.path.join(folder, modality)
    folder = os.path.join(folder, 'dicom')
    return folder


# -----------------------------------------------------------------------------
def insert_dicom_study_from_dataset(db, ds, patient):

    # retrieve patient or create if not exist
    if not patient:
        patient = guess_or_create_patient(db, ds)

    dicom_study = Box()
    dicom_study.study_uid = str(ds.data_element("StudyInstanceUID").value)

    try:
        dicom_study.study_description = ds.data_element("StudyDescription").value
    except:
        dicom_study.study_description = ''
    try:
        dicom_study.study_name = ds[0x0009,0x1010].value.decode("utf-8")
    except:
        dicom_study.study_name = ''

    dicom_study.patient_id = patient.id

    return dicom_study

# -----------------------------------------------------------------------------
def guess_or_create_patient(db, ds):

    # tyy to retrieve patient from PatientID tag
    patient_dicom_id = ds.data_element("PatientID").value
    patient = syd.find_one(db['Patient'], dicom_id=patient_dicom_id)

    # create if not exist
    if patient is None:
        patient = Box()
        patient.dicom_id = patient_dicom_id
        try:
            patient.name = str(ds.data_element("PatientName").value)
            patient.sex = ds.data_element("PatientSex").value
        except:
            pass
        patient.num = 0
        # FIXME --> to complete
        patient = syd.insert_one(db['Patient'], patient)
        tqdm.write('Insert new Patient {}'.format(patient))

    return patient

# -----------------------------------------------------------------------------
def insert_dicom_file_from_dataset(db, ds, filename, dicom_series, future_dicom_files):

    #do_it_later = False
    # print(dicom_series.modality)
    # if dicom_series.modality == 'CT':
    do_it_later = True

    dicom_file = Box()
    dicom_file.sop_uid = ds.data_element("SOPInstanceUID").value
    dicom_file.dicom_series_id = dicom_series.id
    try:
        dicom_file.instance_number = int(ds.InstanceNumber)
    except:
        dicom_file.instance_number = None

    # insert file in folder
    base_filename = os.path.basename(filename)
    afile = Box()
    afile.folder = dicom_series.folder
    afile.filename = base_filename
    # afil.md5 = later
    if not do_it_later:
        afile = syd.insert_one(db['File'], afile)

    # copy the file
    src = filename
    dst_folder = os.path.join(db.absolute_data_folder, dicom_series.folder)
    dst = os.path.join(dst_folder, base_filename)
    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)
    if not do_it_later:
        copyfile(src, dst)

    # insert the dicom_file
    if not do_it_later:
        dicom_file.file_id = afile.id
        syd.insert_one(db['DicomFile'], dicom_file)

    # FIXME special case for CT
    if do_it_later:
        f = Box()
        f.afile = afile
        f.dicom_file = dicom_file
        f.src = src
        f.dst = dst
        future_dicom_files.append(f)

    return dicom_file

# -----------------------------------------------------------------------------
def guess_or_create_injection(db, ds, dicom_study, dicom_series):

    # EXAMPLE

    #(0040, 2017) Filler Order Number / Imaging Servi LO: 'IM00236518'
    #(0054, 0016)  Radiopharmaceutical Information Sequence   1 item(s) ----
    #  (0018, 0031) Radiopharmaceutical                 LO: 'Other'
    #  (0018, 1070) Radiopharmaceutical Route           LO: 'Intravenous route'
    #  (0018, 1072) Radiopharmaceutical Start Time      TM: '111200'
    #  (0018, 1074) Radionuclide Total Dose             DS: "98000000"
    #  (0018, 1075) Radionuclide Half Life              DS: "4062.599854"
    #  (0018, 1076) Radionuclide Positron Fraction      DS: "0.891"
    #  (0018, 1078) Radiopharmaceutical Start DateTime  DT: '20180926111208'
    #  (0054, 0300)  Radionuclide Code Sequence   1 item(s) ----
    #    (0008, 0100) Code Value                          SH: 'C-131A3'
    #    (0008, 0102) Coding Scheme Designator            SH: 'SRT'
    #    (0008, 0104) Code Meaning                        LO: '^68^Galium'

    # 1. try read Radiopharmaceutical Information Sequence
    # 2. Yes: read injection, info
    # 3. try to find one: rad, patient, date, total
    # 4. if no CREATE
    # else
    # try to find one: patient, date --> max delay few days

    try:
        # (0054, 0016) Radiopharmaceutical Information Sequence
        rad_seq = ds[0x0054,0x0016]
        for rad in rad_seq:
            # (0018, 0031) Radiopharmaceutical
            rad_rad = rad[0x0018, 0x0031]
            rad_info = Box()
            # (0054, 0300) Radionuclide Code Sequence
            rad_code_seq = rad[0x0054,0x0300]
            # (0018, 1074) Radionuclide Total Dose
            rad_info.total_dose = rad[0x0018,0x1074].value
            #  (0018, 1076) Radionuclide Positron Fraction
            rad_info.positron_fraction = rad[0x0018,0x1076].value
            rad_info.code = []
            rad_info.date = []
            for code in rad_code_seq:
                # (0008, 0104) Code Meaning
                rad_info.code.append(code[0x0008,0x0104].value)
                # (0018, 1078) Radiopharmaceutical Start DateTime
                rad_info.date.append(rad[0x0018,0x1078].value)
                injection = search_injection_from_info(db, dicom_study, rad_info)
            if not injection:
                injection = new_injection(db, dicom_study, rad_info)
    except:
        #tqdm.write('Cannot find info on radiopharmaceutical in DICOM')
        injection = search_injection(db, ds, dicom_study, dicom_series)

    # return injection (could be None)
    return injection

# -----------------------------------------------------------------------------
def search_injection_from_info(db, dicom_study, rad_info):

    patient_id = dicom_study.patient_id
    all_rad = syd.find(db['Radionuclide'])
    rad_names = [ n.name for n in all_rad]

    if len(rad_info.code) != 1:
        tqdm.write('Error: several radionuclide found. Dont know what to do')
        return None

    # look for radionuclide name and date
    rad_code = rad_info.code[0]
    rad_date = datetime.strptime(rad_info.date[0], '%Y%m%d%H%M%S')
    s = [str_match(rad_code,n) for n in rad_names]
    s = np.array(s)
    i= np.argmax(s)
    rad_name = rad_names[i]

    # search if injections exist for this patient and this rad
    radionuclide = syd.find_one(db['Radionuclide'], name = rad_name)
    rad_info.radionuclide_id = radionuclide.id
    inj_candidates = syd.find(db['Injection'],
                              radionuclide_id = radionuclide.id,
                              patient_id = patient_id)
    if len(inj_candidates) == 0:
        return None

    # check date and activity
    max_time_days = timedelta(1.0) # 1 day # FIXME  <------------------------ options
    found = None
    for ic in inj_candidates:
        d = ic.date
        if d>rad_date:
            t = d-rad_date
        else:
            t = rad_date-d
        if t <= max_time_days:
            act_diff = np.fabs(ic.activity_in_mbq - rad_info.total_dose)
            found = ic
            tqdm.write('Timedelta superior to 10 minutes')

    if found:
        tqdm.write(f'Injection found : {found}')
        return found
    else:
        return None


# -----------------------------------------------------------------------------
def search_injection(db, ds, dicom_study, dicom_series):
    patient_id = dicom_study.patient_id
    inj_candidates = syd.find(db['Injection'], patient_id = patient_id)
    dicom_date = dicom_series.acquisition_date

    # check date is before the dicom
    found = None
    for ic in inj_candidates:
        if ic.date < dicom_date:
            if found:
                if ic.date > found.date:
                    found = ic
                    #tqdm.write('Several injections may be associated. Ignoring injection')
            else:
                found = ic

    if found:
        tqdm.write(f'Injection found : {found}')
        return found
    else:
        return None


# -----------------------------------------------------------------------------
def new_injection(db, dicom_study, rad_info):
    injection = Box()
    injection.radionuclide_id = rad_info.radionuclide_id
    injection.patient_id = dicom_study.patient_id
    injection.activity_in_mbq = rad_info.total_dose/1e6
    injection.date = datetime.strptime(rad_info.date[0], '%Y%m%d%H%M%S')

    syd.insert_one(db['Injection'], injection)
    tqdm.write(f'Insert new injection {injection}')
    return injection


# -----------------------------------------------------------------------------
def get_dicom_image_info(ds):

    sx = sy = sz = '?'
    try:
        sx = ds.Rows
        sy = ds.Columns
        sz = ds.NumberOfFrames
    except:
        pass

    if (sz != '?'):
        img_size = '{}x{}x{}'.format(sx,sy,sz)
    else:
        if (sx == '?' or sy == '?'):
            img_size = None
        else:
            img_size = '{}x{}'.format(sx,sy)

    spacing_x = spacing_y = spacing_z = '?'
    try:
        spacing_x = ds.PixelSpacing[0]
        spacing_y = ds.PixelSpacing[1]
        spacing_z = ds.SliceThickness
    except:
        pass

    if (spacing_z != '?'):
        img_spacing = '{}x{}x{}'.format(spacing_x,spacing_y,spacing_z)
    else:
        if (spacing_x == '?' or spacing_y == '?'):
            img_spacing = None
        else:
            img_spacing = '{}x{}'.format(spacing_x,spacing_y)

    return img_size, img_spacing


# -----------------------------------------------------------------------------
def get_dicom_series_files(db, dicom_series):
    '''
    Return the list of files associated with the dicom_serie
    '''

    # get all dicom files
    dicom_files = syd.find(db['DicomFile'], dicom_series_id=dicom_series['id'])

    # sort by instance_number
    dicom_files = sorted(dicom_files, key=lambda kv:  (kv['instance_number'] is None, kv['instance_number']))

    # get all associated id of the files
    fids = [ df['file_id'] for df in dicom_files]

    # find files
    res = syd.find(db['File'], id=fids)

    # FIXME sort res like fids (?)

    return res


# -----------------------------------------------------------------------------
def insert_future_dicom_files(db, future_dicom_files):

    if len(future_dicom_files) < 1:
        return []

    all_files = [f.afile for f in future_dicom_files]
    all_files = syd.insert(db['File'], all_files)

    if len(future_dicom_files)>1:
        tqdm.write(f'Copying {len(future_dicom_files)} files')
    for f in future_dicom_files:
        copyfile(f.src, f.dst)

    for df, f in zip(future_dicom_files, all_files):
        df.dicom_file.file_id = f.id

    all_dicom_files = [f.dicom_file for f in future_dicom_files]
    all_dicom_files = syd.insert(db['DicomFile'], all_dicom_files)

    return all_dicom_files

