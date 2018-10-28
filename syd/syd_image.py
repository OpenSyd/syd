#!/usr/bin/env python3

import dataset
import pydicom
import itk
from .syd_db import *

# -----------------------------------------------------------------------------
def create_image_table(db):
    '''
    Create the Image table
    '''

    # other fields ?
    # image size dimension spacing etc ?

    # create DicomSerie table
    q = 'CREATE TABLE Image (\
    id INTEGER PRIMARY KEY NOT NULL,\
    patient_id INTEGER NOT NULL,\
    injection_id INTEGER,\
    dicom_serie_id INTEGER,\
    file_mhd_id INTEGER,\
    file_raw_id INTEGER,\
    pixel_type TEXT,\
    pixel_unit TEXT,\
    frame_of_reference_uid TEXT,\
    modality TEXT,\
    FOREIGN KEY(patient_id) REFERENCES Patient(id),\
    FOREIGN KEY(injection_id) REFERENCES Injection(id),\
    FOREIGN KEY(dicom_serie_id) REFERENCES DicomSerie(id),\
    FOREIGN KEY(file_mhd_id) REFERENCES File(id),\
    FOREIGN KEY(file_raw_id) REFERENCES File(id)\
    )'
    result = db.query(q)
    #dicom_serie_table = db['DicomSerie']
    #dicom_serie_table.create_column('acquisition_date', db.types.datetime)
    #dicom_serie_table.create_column('reconstruction_date', db.types.datetime)


# -----------------------------------------------------------------------------
def insert_image_from_dicom(db, ids, pixel_type):
    '''
    Convert several Dicom images to MHD images
    '''

    for id in ids:
        insert_one_image_from_dicom(db, id, pixel_type)


# -----------------------------------------------------------------------------
def insert_one_image_from_dicom(db, id, pixel_type):
    '''
    Convert one Dicom image to MHD image
    '''

    print('insert_one_image_from_dicom', id, pixel_type)

    dicom_serie = db['DicomSerie'].find_one(id=id)
    print(dicom_serie)
    modality = dicom_serie['modality']

    # read dicom image

    # pixel_type

    # write file

    # create file mhd/raw
    path = get_dicom_serie_path(db, dicom_serie)
    img_info = { 'path': path, 'filename': 'not_yet'}
    id_mhd = syd.insert_one(db['File'], img_info)
    id_raw = syd.insert_one(db['File'], img_info)
    img_info['id'] = id_mhd
    img_info['filename'] = str(id_mhd)+'_'+modality+'.mhd'
    i = db['File'].update(img_info, ['id'])
    print(img_info)
    img_info['id'] = id_raw
    img_info['filename'] = str(id_raw)+'_'+modality+'.raw'
    print(img_info)
    db['File'].update(img_info, ['id'])
    print(img_info)

    # create Image
    img_info = {
        'patient_id': dicom_serie['patient_id'],
        'injection_id': dicom_serie['injection_id'],
        'dicom_serie_id': dicom_serie['id'],
        'file_mhd_id': id_mhd,
        'file_raw_id': id_raw,
        'pixel_type': pixel_type,
        'pixel_unit': pixel_unit,
        'frame_of_reference_uid': dicom_serie['frame_of_reference_uid'],
        'modality': modality
    }
    print(img_info)

    # insert Image
    id = insert_one(db['Image'], img_info)
    print(id)

