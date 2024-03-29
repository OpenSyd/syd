#!/usr/bin/env python3

import dataset
import syd
import pydicom
import os
import itk
import numpy as np
from .syd_db import *
import gatetools as gt


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
    dicom_series_id INTEGER,\
    roi_id INTEGER,\
    acquisition_id INTEGER,\
    file_mhd_id INTEGER,\
    file_raw_id INTEGER,\
    pixel_type TEXT,\
    pixel_unit TEXT,\
    frame_of_reference_uid TEXT,\
    modality TEXT,\
    FOREIGN KEY(patient_id) REFERENCES Patient(id) on delete cascade,\
    FOREIGN KEY(injection_id) REFERENCES Injection(id) on delete cascade,\
    FOREIGN KEY(dicom_series_id) REFERENCES DicomSeries(id) on delete cascade,\
    FOREIGN KEY(roi_id) REFERENCES Roi(id) on delete cascade,\
    FOREIGN KEY(file_mhd_id) REFERENCES File(id) on delete cascade,\
    FOREIGN KEY(acquisition_id) REFERENCES Acquisition(id) on delete cascade,\
    FOREIGN KEY(file_raw_id) REFERENCES File(id) on delete cascade\
    )'
    result = db.query(q)
    image_table = db['image']
    image_table.create_column('acquisition_date', db.types.datetime)

    # define trigger
    con = db.engine.connect()
    cur = con.connection.cursor()
    cur.execute('CREATE TRIGGER on_image_delete AFTER DELETE ON Image\
    BEGIN\
    DELETE FROM File WHERE id = OLD.file_mhd_id;\
    DELETE FROM File WHERE id = OLD.file_raw_id;\
    END;')
    con.close()


# -----------------------------------------------------------------------------
def build_image_folder(db, image):
    '''
    Create the file folder of an Image
    '''

    pname = syd.find_one(db['Patient'], id=image['patient_id'])['name']
    # date = image['acquisition_date'].strftime('%Y-%m-%d')
    # modality = image['modality']
    # folder = build_folder(db, pname, date, modality)
    folder = pname
    return folder


# -----------------------------------------------------------------------------
def insert_image_from_dicom(db, dicom_series,dicom_path):
    '''
    Convert one Dicom image to MHD image
    '''

    # modality
    modality = dicom_series['modality']

    #Try guessing pixel unit from dicom
    try:
        ds = pydicom.read_file(dicom_path)
        unit = ds[0x0054,0x1001].value
        if unit == "BQML":
            pixel_unit = 'Bq/mL'
        else:
            pixel_unit=unit
    except:

        # guess pixel unit FIXME --> check dicom tag ?
        pixel_unit = 'undefined'
        if modality == 'CT':
            pixel_unit = 'HU'
        if modality == 'NM':
            pixel_unit = 'counts'
        if modality == 'RTDOSE':
            pixel_unit = 'Gy'


    # get dicom files
    files = syd.get_dicom_series_files(db, dicom_series)
    if len(files) == 0:
        s = 'Error, no file associated with this dicom serie'
        syd.raise_except(s)

    # get folder
    folder = dicom_series['folder']
    folder = os.path.join(db.absolute_data_folder, folder)
    acquisition_id = int(os.path.basename(os.path.dirname(folder)).split('_')[1])
    suid = dicom_series['series_uid']

    PixelType = itk.ctype('float')
    Dimension = 3

    namesGenerator = itk.GDCMSeriesFileNames.New()
    namesGenerator.SetUseSeriesDetails(False)
    namesGenerator.AddSeriesRestriction("0008|0021")
    namesGenerator.SetGlobalWarningDisplay(False)
    namesGenerator.SetDirectory(folder)
    seriesUID = namesGenerator.GetSeriesUIDs()
    fileNames = namesGenerator.GetFileNames(seriesUID[0])

    # read dicom image
    if len(fileNames) > 1:
        itk_image = gt.read_dicom(fileNames)
    else:
        itk_image = gt.read_3d_dicom(fileNames)

    # pixel_type (ignored)
    # pixel_type = image.GetPixelIDTypeAsString()

    # GetNumberOfComponentsPerPixel

    # convert: assume only 2 type short for CT and float for everything else
    pixel_type = 'float'
    if modality == 'CT':
        pixel_type = 'signed_short'
        InputImageType = itk.Image[itk.F, Dimension]
        OutputImageType = itk.Image[itk.SS, Dimension]

        castImageFilter = itk.CastImageFilter[InputImageType, OutputImageType].New()
        castImageFilter.SetInput(itk_image)
        castImageFilter.Update()
        itk_image = castImageFilter.GetOutput()

    #    else:
    #        pixel_type = 'float'
    #        try:
    #            itk_image = sitk.Cast(itk_image, sitk.sitkFloat32)
    #        except:
    #            s = 'Cannot cast image. Ignoring '+str(dicom_series)
    #            warning(s)
    #            return None

    # injection ?
    injid = None
    if 'injection_id' in dicom_series:
        injid = dicom_series.injection_id

    # create Image
    #syd.update_nested_one(db, dicom_series)
    labels = ''
    if 'labels' in dicom_series:
        labels = dicom_series.labels
    dicom_study = syd.find_one(db['DicomStudy'], id=dicom_series.dicom_study_id)
    patient = syd.find_one(db['Patient'], id = dicom_study.patient_id)
    img = {
        'patient_id': patient.id,
        'injection_id': injid,
        'dicom_series_id': dicom_series.id,
        'acquisition_id': acquisition_id,
        'pixel_type': pixel_type,
        'pixel_unit': pixel_unit,
        'frame_of_reference_uid': dicom_series.frame_of_reference_uid,
        'modality': modality,
        'acquisition_date': dicom_series.acquisition_date,
        'labels': labels
    }

    # insert the image in the db
    img = syd.insert_new_image(db, img, itk_image)

    # write the mhd file
    p = syd.get_image_filename(db, img)
    itk.imwrite(itk_image, p)

    return img


# -----------------------------------------------------------------------------
def get_image_patient(db, image):
    '''
    Retrieve the patient associated with the image
    '''
    patient = syd.find_one(db['Patient'], id=image['patient_id'])
    return patient


# -----------------------------------------------------------------------------
def get_image_filename(db, image):
    '''
    Retrieve the filename associated with the image
    '''
    file_mhd = syd.find_one(db['File'], id=image['file_mhd_id'])
    filepath = get_file_absolute_filename(db, file_mhd)
    return filepath


# -----------------------------------------------------------------------------
def read_itk_image(db, image):
    '''
    Retrieve the filename associated with the image and read the itk image
    '''
    p = get_image_filename(db, image)
    itk_image = itk.imread(p)

    return itk_image


# -----------------------------------------------------------------------------
def insert_new_image(db, img, itk_image):
    '''
    Create a new image in the database: DO NOT COPY itk_image in the db.
    Should be performed after:
               p = syd.get_image_filename(db, img)
               itk.imwrite(itk_image, p)
    img : dict
    itk_image : image itk
    '''

    # set the id to None to force a new image
    #img['id'] = None

    # insert Image to get the id
    img = syd.insert_one(db['Image'], img)

    # create file mhd/raw
    folder = build_image_folder(db, img)
    if not os.path.exists(os.path.join(db.absolute_data_folder, folder)):
        os.makedirs(os.path.join(db.absolute_data_folder, folder))
    modality = img['modality']
    id = img['id']
    file_mhd = syd.new_file(db, folder, str(id) + '_' + modality + '.mhd')
    file_raw = syd.new_file(db, folder, str(id) + '_' + modality + '.raw')

    # FIXME check and set image_type

    # update files in img
    img['file_mhd_id'] = file_mhd['id']
    img['file_raw_id'] = file_raw['id']
    syd.update_one(db['Image'], img)

    return img


# -----------------------------------------------------------------------------
def insert_write_new_image(db, image, itk_image, tags=[]):
    '''
    Create a new image in the database and WRITE the itk_image
    (id will be changed)
    '''

    if len(tags) != 0:
        syd.add_tags(image, tags)
    image = syd.insert_new_image(db, image, itk_image)
    p = syd.get_image_filename(db, image)
    itk.imwrite(itk_image, p)

    return image
