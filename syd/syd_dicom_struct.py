#!/usr/bin/env python3

import dataset
import os
import syd
import pydicom
import tqdm
import gatetools as gt
import itk
from pathlib import Path
from box import Box
from tqdm import tqdm
from shutil import copyfile


# -----------------------------------------------------------------------------
def create_dicom_struct_table(db):
    """
    Create DicomStruct table
    """
    # create DicomStruct table
    q = 'CREATE TABLE DicomStruct (\
    id INTEGER PRIMARY KEY NOT NULL,\
    dicom_series_id INTEGER NOT NULL,\
    frame_of_reference_uid INTEGER,\
    names TEXT,\
    series_uid INTEGER,\
    FOREIGN KEY(dicom_series_id) REFERENCES DicomSeries(id) on delete cascade\
    )'
    result = db.query(q)


# -----------------------------------------------------------------------------
def insert_struct_from_file(db, filename):
    """
    Insert a DicomStruct from a filename
    """

    struct = Box()
    try:
        ds = pydicom.read_file(filename)
    except:
        tqdm.write('Ignoring {}: not a Structure'.format(Path(filename).name))
        return {}

    if ds.Modality != 'RTSTRUCT':
        return {}
    try:
        sop_uid = ds.data_element("SOPInstanceUID").value
    except:
        tqdm.write('Ignoring {}: cannot read UIDs'.format(filename))
        return {}

    # check if the file already exist in the  db
    dicom_file = syd.find_one(db['DicomFile'], sop_uid=sop_uid)
    if dicom_file is not None:
        tqdm.write('Ignoring {}: Dicom SOP Instance already in the db'.format(Path(filename)))
        return {}

    try:
        frame_of_ref = ds.ReferencedFrameOfReferenceSequence[0]
        study = frame_of_ref.RTReferencedStudySequence[0]
        series_uid = study.RTReferencedSeriesSequence[0].SeriesInstanceUID
    except:
        tqdm.write('Ignoring {}: Cannot read SeriesInstanceUID'.format(Path(filename).name))
        return {}

    try:
        dicom_serie = syd.find_one(db['DicomSeries'], series_uid=series_uid)
    except:
        tqdm.write('Ignoring {} : Cannot read DicomSeries'.format(Path(filename).name))

    if dicom_serie is not None:
        struct_names = [str(ssroi.ROIName) for ssroi in ds.StructureSetROISequence]
        separator = ';'
        struct_names = separator.join(struct_names)
        struct = {'dicom_series_id': dicom_serie['id'], 'names': struct_names, 'series_uid': series_uid,
                  'frame_of_reference_uid': dicom_serie['frame_of_reference_uid']}
        struct = syd.insert_one(db['DicomStruct'], struct)
        dicom_file = insert_file(db, ds, filename, struct)
        return struct

    else:
        tqdm.write('Ignoring {} : Cannot find matching DicomSeries'.format(Path(filename).name))
        return {}


# -----------------------------------------------------------------------------
def insert_file(db, ds, filename, struct):
    '''
     Insert or update a dicom from a file
    '''

    dicom_file = Box()
    dicom_file.sop_uid = ds.data_element('SOPInstanceUID').value
    dicom_file.dicom_series_id = struct['dicom_series_id']
    dicom_file.dicom_struct_id = struct['id']
    dicom_series = syd.find_one(db['DicomSeries'], id=struct['dicom_series_id'])
    try:
        dicom_file.instance_number = int(ds.InstanceNumber)
    except:
        dicom_file.instance_number = None

    # insert file in folder
    base_filename = os.path.basename(filename)
    afile = Box()
    afile.folder = dicom_series.folder
    afile.filename = base_filename
    afile = syd.insert_one(db['File'], afile)

    # copy the file
    src = filename
    dst_folder = os.path.join(db.absolute_data_folder, dicom_series.folder)
    dst = os.path.join(dst_folder, base_filename)
    if not os.path.exists(dst_folder):
        os.makedirs(dst_folder)
    # if not do_it_later:
    copyfile(src, dst)

    dicom_file.file_id = afile.id
    dicom_file = syd.insert_one(db['DicomFile'], dicom_file)

    return dicom_file


# -----------------------------------------------------------------------------
def insert_roi_from_struct(db, struct, crop):
    """
    Insert an ROI from a DicomStruct file
    """

    roi = []
    series_id = struct['dicom_series_id']
    dicom_series = syd.find_one(db['DicomSeries'], id=series_id)
    acquisition = syd.find_one(db['Acquisition'], id=dicom_series['acquisition_id'])
    injection_id = acquisition['injection_id']
    acquisition_id = dicom_series['acquisition_id']
    injection = syd.find_one(db['Injection'], id=injection_id)
    patient = syd.find_one(db['Patient'], id=injection['patient_id'])

    ### Getting the CT image path ###
    image_ct = syd.find_one(db['Image'], dicom_series_id=series_id)
    try:
        file_img = syd.find_one(db['File'], id=image_ct['file_mhd_id'])
    except:
        print('Could not find the CT image in the database')
    filename_img = db.absolute_data_folder + '/' + file_img['folder'] + '/' + file_img['filename']

    ### Getting the DicomStruct dicom path ###
    dicom_file = syd.find_one(db['DicomFile'], dicom_struct_id=struct['id'])
    file_struct = syd.find_one(db['File'], id=dicom_file['file_id'])
    filename_struct = db.absolute_data_folder + '/' + file_struct['folder'] + '/' + file_struct['filename']

    ### Using GateTools to extract the image from the Dicom File ###
    structset = pydicom.read_file(filename_struct)
    img = itk.imread(filename_img)
    base_filename, extension = os.path.splitext(filename_img)
    roi_names = gt.list_roinames(structset)
    roi_objs = list()
    npbar = 0
    pbar = None
    for r in roi_names:
        try:
            aroi = gt.region_of_interest(structset, r)
            if not aroi.have_mask():
                tqdm.write(f'Mask for {r} not possible')
            roi_objs.append(aroi)
        except:
            tqdm.write(f'Something is wrong with ROI {r}')
            roi.remove(r)
    if npbar > 0:
        pbar = tqdm(total=npbar, leave=False)
    for roiname, aroi in zip(roi_names, roi_objs):
        try:
            mask = aroi.get_mask(img, corrected=False, pbar=pbar)
            if crop:
                mask = gt.image_auto_crop(mask, bg=0)
            output_filename = base_filename + '_' + ''.join(e for e in roiname if e.isalnum()) + '.mhd'
            itk.imwrite(mask, output_filename)
            im = {'patient_id': patient['id'], 'injection_id': injection_id, 'acquisition_id': acquisition_id,
                  'frame_of_reference_uid': dicom_series['frame_of_reference_uid'], 'modality': 'RTSTRUCT',
                  'labels': None}
            im = syd.insert_write_new_image(db, im, itk.imread(output_filename))
            roi = {'dicom_struct_id': struct['id'], 'image_id': im['id'],
                   'frame_of_reference_uid': struct['frame_of_reference_uid'], 'names': roiname, 'labels': None}
            roi = syd.insert_one(db['Roi'], roi)
            im['roi_id'] = roi['id']
            syd.update_one(db['Image'], im)

        except:
            tqdm.write(f'Error in {roiname, aroi}')
    if npbar > 0:
        pbar.close()


# -----------------------------------------------------------------------------
def get_dicom_struct_files(db, struct):
    """
    Return the list of files associated with the struct
    """
    dicom_files = syd.find(db['DicomFile'], dicom_struct_id=struct['id'])

    # sort by instance_number
    dicom_files = sorted(dicom_files, key=lambda kv: (kv['instance_number'] is None, kv['instance_number']))

    # get all associated id of the files
    fids = [df['file_id'] for df in dicom_files]

    # find files
    res = syd.find(db['File'], id=fids)

    # FIXME sort res like fids (?)

    return res
