#!/usr/bin/env python3

import dataset
import syd
import itk
from pathlib import Path
from box import Box
from tqdm import tqdm


# -----------------------------------------------------------------------------
def create_roi_table(db):
    '''
    Create ROI table
    '''
    # Create ROI table
    q = 'CREATE TABLE Roi (\
    id INTEGER PRIMARY KEY NOT NULL,\
    dicom_struct_id INTEGER,\
    image_id INTEGER,\
    frame_of_reference_uid,\
    names TEXT,\
    FOREIGN KEY(dicom_struct_id) REFERENCES DicomStruct(id) on delete cascade,\
    FOREIGN KEY(image_id) REFERENCES Image(id) on delete cascade\
    )'
    result = db.query(q)


# -----------------------------------------------------------------------------
def insert_roi_from_file(db, filename, dicom_series):
    '''
    Insert a ROI from a filename
    '''
    struct = Box()
    # if Path(filename).suffix != 'mha' or Path(filename).suffix != 'mhd':
    #     tqdm.write('Ignoring {}: not an Image'.format(Path(filename).name))
    #     return {}
    # else:
    injection_id = dicom_series['injection_id']
    acquisition_id = dicom_series['acquisition_id']
    acquisition = syd.find_one(db['Acquisition'], id=acquisition_id)
    injection = syd.find_one(db['Injection'], id=acquisition['injection_id'])
    patient = syd.find_one(db['Patient'], id=injection['patient_id'])
    im = {'patient_id': patient['id'], 'injection_id': injection_id, 'acquisition_id': acquisition_id,
          'frame_of_reference_uid': dicom_series['frame_of_reference_uid'], 'modality': 'RTSTRUCT', 'labels': None}
    e = syd.insert_write_new_image(db, im, itk.imread(filename))
    try:
        struct = syd.find_one(db['DicomStruct'], dicom_series_id=dicom_series['id'])
    except:
        tqdm.write(f'Cannot find DicomStruct matching {filename}')
    roi = {'dicom_struct_id': struct['id'], 'image_id': e['id'], 'names': struct['names'],
           'frame_of_reference_uid': dicom_series['frame_of_reference_uid'], 'labels': None}
    e = syd.insert_one(db['Roi'], roi)
    return e
