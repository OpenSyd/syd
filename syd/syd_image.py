#!/usr/bin/env python3

import dataset
import pydicom
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


