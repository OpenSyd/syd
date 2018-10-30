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
def build_image_folder(db, image):
    '''
    Create the file folder of an Image
    '''

    pname = db['Patient'].find_one(id=image['patient_id'])['name']
    date = image['acquisition_date'].strftime('%Y-%m-%d')
    modality = image['modality']
    folder = build_folder(db, pname, date, modality)
    return folder

# -----------------------------------------------------------------------------
def insert_one_image_from_dicom(db, id, pixel_type):
    '''
    Convert one Dicom image to MHD image
    '''

    # get the dicom_serie
    dicom_serie = db['DicomSerie'].find_one(id=id)

    # modality
    modality = dicom_serie['modality']

    # guess pixel unit FIXME --> check dicom tag ?
    pixel_unit = 'undefined'
    if modality == 'CT':
        pixel_unit = 'HU'
    if modality == 'NM':
        pixel_unit = 'counts'
    if modality == 'PT':
        pixel_unit = 'MBq/mL'

    # create Image
    img = {
        'patient_id': dicom_serie['patient_id'],
        'injection_id': dicom_serie['injection_id'],
        'dicom_serie_id': dicom_serie['id'],
        #'file_mhd_id': id_mhd,
        #'file_raw_id': id_raw,
        #'pixel_type': pixel_type,
        'pixel_unit': pixel_unit,
        'frame_of_reference_uid': dicom_serie['frame_of_reference_uid'],
        'modality': modality,
        'acquisition_date': dicom_serie['acquisition_date']
    }

    # insert Image
    img = syd.insert_one(db['Image'], img)

    # build folder name (pname/date/modality)
    folder = build_image_folder(db, img)

    # create file mhd/raw
    file_mhd = syd.new_file(db, folder, 'not_yet')
    file_raw = syd.new_file(db, folder, 'not_yet')

    # use id in the filename
    id = img['id']
    file_mhd['filename'] = str(id)+'_'+modality+'.mhd'
    file_raw['filename'] = str(id)+'_'+modality+'.raw'
    syd.update_one(db['File'], file_mhd)
    syd.update_one(db['File'], file_raw)

    # get dicom files
    files = syd.get_dicom_serie_files(db, dicom_serie)
    if len(files) == 0:
        s = 'Error, no file associated with this dicom serie'
        raise_except(s)

    # get folder
    folder = dicom_serie['folder']
    folder = os.path.join(db.absolute_data_folder, folder)
    suid = dicom_serie['series_uid']

    # read dicom image
    image = None
    if len(files) > 1:
        # sort filenames
        series_file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(folder, suid)
        series_reader = sitk.ImageSeriesReader()
        series_reader.SetFileNames(series_file_names)
        image = series_reader.Execute()
    else:
        filename = get_file_absolute_filename(db, files[0])
        image = sitk.ReadImage(filename)

    # pixel_type
    pixel_type = image.GetPixelIDTypeAsString()

    # write file
    filepath = get_file_absolute_filename(db, file_mhd)
    print('filepath', filepath)
    sitk.WriteImage(image, filepath)

    # update img
    img['file_mhd_id'] = file_mhd['id']
    img['file_raw_id'] = file_raw['id']
    img['pixel_type'] = pixel_type
    syd.update_one(db['Image'], img)

    return img

