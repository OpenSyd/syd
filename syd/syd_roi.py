#!/usr/bin/env python3

import dataset
import syd
import itk
from box import Box
from tqdm import tqdm
import os
import pydicom
import numpy as np
import gatetools as gt



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
    volume TEXT,\
    mass TEXT, \
    density TEXT, \
    name TEXT,\
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
    roi = {'dicom_struct_id': struct['id'], 'image_id': e['id'], 'name': struct['names'],
           'frame_of_reference_uid': dicom_series['frame_of_reference_uid'], 'labels': None}
    e = syd.insert_one(db['Roi'], roi)
    return e

# -----------------------------------------------------------------------------
def update_roi_characteristics(db , r, background=0):
    '''
    Update roi volume, density and mass 
    '''
    im_roi = syd.find_one(db['Image'], roi_id = r['id'])
    dicom_struct = syd.find_one(db['DicomStruct'], id = r['dicom_struct_id'])
    if dicom_struct is not None:
        im_ct = syd.find_one(db['Image'], dicom_series_id=dicom_struct['dicom_series_id'])
    else:
        im_ct = syd.find_one(db['Image'], frame_of_reference_uid=r['frame_of_reference_uid'],modality='CT')
    file_img = syd.find_one(db['File'], id = im_roi['file_mhd_id'])
    if im_ct is not None:
        file_img_ct = syd.find_one(db['File'], id = im_ct['file_mhd_id'])
    else:
        print(f'Could not find the CT file image for the roi {r.id}')
        return 0
    filename_im = os.path.join(db.absolute_data_folder,os.path.join(file_img['folder'], file_img['filename']))
    filename_ct = os.path.join(db.absolute_data_folder, os.path.join(file_img_ct['folder'], file_img_ct['filename']))
    roi = itk.imread(filename_im,itk.F)
    ct = itk.imread(filename_ct,itk.F)
    array_im = itk.array_from_image(roi).astype(float)
    spacing = roi.GetSpacing()

    ### Volume ###
    e = np.count_nonzero(array_im != background)
    volume_elem = spacing[0]*spacing[1]*spacing[2] # spacing is in mm
    volume_elem = volume_elem * 0.001 # convert mm3 to cm3 (/1000)
    volume = e* volume_elem
    r['volume']=volume 
    syd.update_one(db['Roi'], r)

    ### Density ###
    mask = gt.applyTransformation(input=roi, like=ct, force_resample=True,interpolation_mode ='NN')
    stats = gt.imageStatistics(input=ct,mask=mask)
    HU_mean = stats['mean']
    density = 1+(HU_mean/1000)
    r['density'] = density
    syd.update_one(db['Roi'],r)

    ### Mass ###
    mass = np.multiply(volume,density)
    r['mass'] = mass
    syd.update_one(db['Roi'], r)

    return 1

# -----------------------------------------------------------------------------
def get_roi_file_absolute_filename(db,e):
    image = syd.find_one(db['Image'], id=e['image_id'])
    filepath = syd.get_image_filename(db,image)
    return filepath

