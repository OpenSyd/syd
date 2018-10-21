#!/usr/bin/env python3

import dataset
import pydicom
import os
import pathlib
from collections import defaultdict
from .syd_helpers import *
from .syd_db import *

# -----------------------------------------------------------------------------
def create_dicomserie_table(db):
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
    dataset_name TEXT)'
    result = db.query(q)
    dicomserie_table = db['DicomSerie']
    dicomserie_table.create_column('acquisition_date', db.types.datetime)
    dicomserie_table.create_column('reconstruction_date', db.types.datetime)


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
                print('Ignoring {}: cannot find SeriesInstanceUID'.format(f))
            # ignore unmanaged modality
            modality = ds.Modality
            if (modality == 'CT' or modality == 'PT' or modality == 'NM'):
                s = {'sid':sid, 'f':f, 'ds': ds}
                dicoms.append(s)
            else:
                print('Ignoring {}: modality is {}'.format(f,modality))
        except:
            print('Ignoring {}: (not a dicom)'.format(f))

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
    print('Found {} Dicom series.'.format(len(series)))
    for k,v in series.items():
        insert_dicom_serie(db, v['f'], v['ds'], patient_id)


# -----------------------------------------------------------------------------
def insert_dicom_serie(db, files, dicom_datasets, patient_id):
    '''
    Insert one dicom serie, with all associated files
    If patient_id is 0, try to guess
    '''

    # consider only the first dataset
    ds = dicom_datasets[0]
    sid = ds.data_element('SeriesInstanceUID').value
    print(sid)

    # check if this series already exist FIXME

    # get patient_id
    if (patient_id == 0):
        patient_id = guess_patient_from_dicom(db, ds)

    # check if patient exist
    try:
        p = db['Patient'].find_one(id=patient_id)
    except:
        print('Error, cannor find the patient with id {}'.format(patient_id))
        print('The dicom serie {} is ignored.'.format(sid))
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
    print(acquisition_date, reconstruction_date)

    # get tag values that are bytes, not string
    try:
        study_name = ds[0x0009,0x1010].value.decode("utf-8")
    except:
        study_name = ''
    try:
        dataset_name = ds[0x0011, 0x1012].value.decode("utf-8")
    except:
        dataset_name = ''

    # build info
    info = {
        'patient_id': 1,
        #'injection_id': 1,
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
    db['DicomSerie'].insert(info)

    # FIXME create elements DicomFile or File ?

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

    if (len(found) == 0):
        print('Cannot guess patient from dicom.')
        return 0
    if (len(found) > 1):
        print('Several patients found with dicomID = {}, bug !?'.format(pid))
        return 0

    return found[0]['id']

