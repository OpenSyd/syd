#!/usr/bin/env python3

import dataset
import pydicom
import os
import pathlib
from collections import defaultdict

# -----------------------------------------------------------------------------
def create_dicomserie_table(db):
    '''
    Create the DicomSerie table
    '''

    #id patient dicom_study_uid dicom_series_uid
    # dicom_frame_of_reference_uid dicom_modality
    #dicom_description dicom_series_description dicom_study_description dicom_study_name
    #dicom_study_id dicom_image_id dicom_dataset_name
    #dicom_manufacturer
    #dicom_manufacturer_model_name dicom_software_version dicom_patient_name

    #dicom_patient_id dicom_patient_birth_date dicom_patient_sex typeid

    #injection dicom_acquisition_date dicom_reconstruction_date

    # dicom_pixel_scale
    #dicom_pixel_offset dicom_window_center dicom_window_width dicom_radionuclide_name
    #dicom_counts_accumulated dicom_actual_frame_duration_in_msec
    #dicom_number_of_frames_in_rotation dicom_number_of_rotations dicom_table_traverse_in_mm
    #dicom_table_height_in_mm dicom_rotation_angle dicom_real_world_value_slope
    #dicom_real_world_value_intercept

    # create DicomSerie table
    q = 'CREATE TABLE DicomSerie (\
    id INTEGER PRIMARY KEY NOT NULL,\
    patient_id INTEGER NOT NULL,\
    series_uid INTEGER NOT NULL,\
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
def insert_dicom(db, folder):
    '''
    Search for Dicom Series in the folder and insert in the database.

    Options FIXME
    - for each NM serie -> associate injection/patient
    - what about several series ?
    - recursive
    - option: copy or link files in the db image folder
    - what kind of tags stored in the tables ?? how stored ?

    '''

    # open folder, get files
    # read all files (!), find list of dicom series
    # output : 1 dicomserie, 1 list of file

    # for each dicom serie
    #     find how to associate with injection/patient
    #     store dicomserie in the table
    #     for all files (bulk)
    #             create filename
    #             store file in the table, as dicomfiles (not file ?)
    #             copy/link all elements

    # get all the files ()recursively)
    files = list(pathlib.Path(folder).rglob("*"))
    print('Found {} files in the folder and subfolders.'.format(len(files)))

    # read all dicom dataset to get the SeriesInstanceUID
    # store the sid, the filename and the dicom dataset
    dicoms = []
    for f in files:
        f = str(f)
        try:
            ds = pydicom.read_file(f)
            try:
                sid = ds.data_element("SeriesInstanceUID").value
            except:
                print('Ignoring {}: cannot find SeriesInstanceUID'.format(f))
            s = {'sid':sid, 'f':f, 'ds': ds}
            dicoms.append(s)
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
            series[sid] = { 'f':[f], 'ds':[ds]}

    # create series
    print('Found {} Dicom series.'.format(len(series)))
    for k,v in series.items():
        insert_dicom_serie(db, k, v['f'], v['ds'])


# -----------------------------------------------------------------------------
def insert_dicom_serie(db, sid, files, dicom_datasets):
    '''
    FIXME
    '''

    print('insert ', sid, len(files), len(dicom_datasets))

    # create element DicomSerie
    # patient_id INTEGER NOT NULL,\
    # series_uid INTEGER NOT NULL,\
    # study_uid INTEGER NOT NULL,\
    # modality TEXT,\
    # series_description TEXT,\
    # study_description TEXT,\
    # study_name TEXT,\
    # dataset_name TEXT)'
    # result = db.query(q)
    # dicomserie_table = db['DicomSerie']
    # dicomserie_table.create_column('acquisition_date', db.types.datetime)
    # dicomserie_table.create_column('reconstruction_date', db.types.datetime)

    ds = dicom_datasets[0] # get the first one

    # get date FIXME manage errors (use instance creation if not found)
    acquisition_date = syd.str_to_date(ds.data_element("AcquisitionDate")+' '+
                         ds.data_element("AcquisitionTime"))
    recontruction_date = syd.str_to_date(ds.data_element("ContentDate")+' '+
                                         ds.data_element("ContentTime"))
    print(acquisition_date, recontruction_date)

    # guess patient+ injection ?
    # if CT -> no injection
    # if NM ->

    # build info
    info = {
        'patient_id': 1,
        'series_uid': ds.data_element("SeriesInstanceUID"),
        'study_uid':  ds.data_element("StudyInstanceUID"),
        'frame_of_reference_uid':  ds.data_element("FrameOfReferenceUID"),
        'modality': modality,
        'series_description': ds.data_element("SeriesDescription"),
        'study_description': ds.data_element("StudyDescription"),
        'study_name': ds.data_element("StudyName"),
        'dataset_name': ds.data_element("DatasetName"),
        'acquisition_date': acquisition_date,
        'reconstruction_date': reconstruction_date,
    }

    syd.insert(db['DicomSerie'], info) ## later -> bulk insert ?

    # create elements DicomFile or File ?

