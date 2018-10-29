#!/usr/bin/env python3

import dataset
import pydicom
import os
import SimpleITK as sitk
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
    image_table = db['Image']
    image_table.create_column('acquisition_date', db.types.datetime)
    #dicom_serie_table.create_column('reconstruction_date', db.types.datetime)


# -----------------------------------------------------------------------------
def insert_image_from_dicom(db, ids, pixel_type):
    '''
    Convert several Dicom images to MHD images
    '''

    for id in ids:
        insert_one_image_from_dicom(db, id, pixel_type)


# -----------------------------------------------------------------------------
def build_image_path(db, image):
    '''
    Create the file path of an Image
    '''

    pname = db['Patient'].find_one(id=image['patient_id'])['name']
    date = image['acquisition_date'].strftime('%Y-%m-%d')
    modality = image['modality']
    path = get_path(db, pname, date, modality)
    return path

# -----------------------------------------------------------------------------
def insert_one_image_from_dicom(db, id, pixel_type):
    '''
    Convert one Dicom image to MHD image
    '''

    print('insert_one_image_from_dicom', id, pixel_type)

    dicom_serie = db['DicomSerie'].find_one(id=id)
    print(dicom_serie)
    modality = dicom_serie['modality']

    # create Image
    img = {
        'patient_id': dicom_serie['patient_id'],
        'injection_id': dicom_serie['injection_id'],
        'dicom_serie_id': dicom_serie['id'],
        #'file_mhd_id': id_mhd,
        #'file_raw_id': id_raw,
        #'pixel_type': pixel_type,
        #'pixel_unit': pixel_unit,
        #'frame_of_reference_uid': dicom_serie['frame_of_reference_uid'],
        'modality': modality,
        'acquisition_date': dicom_serie['acquisition_date']
    }
    print(img)

    # insert Image
    img = syd.insert_one(db['Image'], img)
    print(img)

    # build path name
    path = build_image_path(db, img)
    print(path)

    # create file mhd/raw
    file_mhd = syd.new_file(db, path, 'not_yet')
    file_raw = syd.new_file(db, path, 'not_yet')
    print(file_mhd, file_raw)

    id_mhd = file_mhd['id']
    file_mhd['filename'] = str(id_mhd)+'_'+modality+'.mhd'
    id_raw = file_raw['id']
    file_raw['filename'] = str(id_raw)+'_'+modality+'.raw'

    syd.update_one(db['File'], file_mhd)
    syd.update_one(db['File'], file_raw)

    print(file_mhd)
    print(file_raw)

    # get dicom files
    dicom_files = db['DicomFile'].find(dicom_serie_id=dicom_serie['id'])
    filenames = []
    for df in dicom_files:
        p = get_file_absolute_filename(db, df['file_id'])
        filenames.append(p)

    # read dicom image
    image = None
    if len(filenames) > 1:
        series_reader = sitk.ImageSeriesReader()
        series_reader.SetFileNames(filenames)
        image = series_reader.Execute()
    else:
        image = sitk.ReadImage(filenames[0])

    # pixel_type
    # FIXME LATER

    # write file
    filepath = get_file_absolute_filename(db, id_mhd)
    print('filepath', filepath)
    #sitk.WriteImage(image, )
    exit(0)

