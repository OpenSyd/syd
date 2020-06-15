#!/usr/bin/env python3
import syd
import sys
from tqdm import tqdm
from datetime import datetime
from datetime import timedelta
from box import Box
import numpy as np
from .syd_helpers import *
import pydicom
import difflib
import itk
import syd.syd_algo.stitch_image as sti


### Patient ###
def guess_or_create_patient(db, ds):
    # try to retrieve patient from PatientID tag
    patient_dicom_id = ds.data_element("PatientID").value
    patient = syd.find_one(db['Patient'], dicom_id=patient_dicom_id)

    # create if not exist
    if patient is None:
        patient = Box()
        patient.dicom_id = patient_dicom_id
        try:
            patient.name = str(ds.data_element("PatientName").value)
            patient.sex = ds.data_element("PatientSex").value
        except:
            pass
        patient.num = 0
        # FIXME --> to complete
        patient = syd.insert_one(db['Patient'], patient)
        tqdm.write('Insert new Patient {}'.format(patient))

    return patient


# -----------------------------------------------------------------------------

### Acquisition ###
def nearest_acquisition(db, date, patient, **kwargs):
    tmp = syd.find_one(db['Acquisition'], date=date)
    if tmp: # if an acquisition already exist no need to find or
        return tmp
    else:
        t = kwargs.get('t', None)
        modality = kwargs.get('modality', None)
        content_type = kwargs.get('content_type', None)
        injection = syd.nearest_injection(db, date, patient)

        if t == 'Listmode':
            dicom = syd.find(db['DicomSeries'], injection_id=injection['id'])
            if dicom != []:
                for d in dicom:
                    if d['modality'] == modality and d['content_type'] == content_type:
                        acquisition = syd.find_one(db['Acquisition'], id=d['acquisition_id'])
                        return acquisition
            else:  # when no dicom are in the database
                result = None
                try:
                    acq = syd.find(db['Acquisition'], injection_id=injection['id'])
                except:
                    tqdm.write('Cannot find acquisition')
                if acq != []:
                    minnimum = np.abs(date - acq[0]['date'])
                    for tmp in acq:
                        m = np.abs(date - tmp['date'])
                        if m <= timedelta(1.0 / 24.0 / 60.0 * 10.0):
                            # timedelta usefull for multiple listmode for example tomo + wholebody
                            if m <= minnimum:
                                minnimum = m
                                result = tmp
                    return result

        elif t == 'Dicom':
            result = None
            # try:
            acq = syd.find(db['Acquisition'], injection_id=injection['id'])
            # except:
            #     tqdm.write('Cannot find acquisition')
            if acq:
                minnimum = np.abs(date - acq[0]['date'])
                for tmp in acq:
                    m = np.abs(date - tmp['date'])
                    if m <= timedelta(1.0 / 24.0 / 60.0 * 10.0):
                        # timedelta usefull for multiple listmode for example tomo + wholebody
                        if m < minnimum:
                            minnimum = m
                            result = tmp

                return result


# -----------------------------------------------------------------------------
def guess_or_create_acquisition(db, dicom_series, patient):
    # try: #try to found or create acquisition
    acquisition_date = dicom_series.acquisition_date
    injection = syd.nearest_injection(db, acquisition_date, patient)
    acquisition = nearest_acquisition(db, acquisition_date, patient, t='Dicom')
    if not acquisition:
        acquisition = new_acquisition(db, dicom_series, acquisition_date, injection)

    # except:
    #     s = 'No Acquisition found'
    #     syd.raise_except(s)
    # print('Except')
    # acquisition_date = dicom_series.acquisition_date
    # try:
    #     acquisition = syd.find_one(db['Acquisition'], date=acquisition_date, modality=dicom_series.Modality)
    #     tqdm.write(f'Acquisition found :{acquisition}')
    # except:
    #     acquisition = None
    #     tqdm.write('No acquisition found')

    return acquisition


# -----------------------------------------------------------------------------
def new_acquisition(db, dicom_series, date, injection):
    acquisition = Box()
    acquisition.injection_id = injection['id']
    acquisition.date = date
    acquisition.modality = dicom_series.modality

    syd.insert_one(db['Acquisition'], acquisition)
    tqdm.write(f'Insert new Acquisition {acquisition}')
    return acquisition


# -----------------------------------------------------------------------------

### Injection ###

def new_injection(db, dicom_study, rad_info):
    injection = Box()
    injection.radionuclide_id = rad_info.radionuclide_id
    injection.patient_id = dicom_study.patient_id
    injection.activity_in_mbq = rad_info.total_dose / 1e6
    injection.date = datetime.strptime(rad_info.date[0], '%Y%m%d%H%M%S')

    syd.insert_one(db['Injection'], injection)
    tqdm.write(f'Insert new injection {injection}')
    return injection


# -----------------------------------------------------------------------------
def nearest_injection(db, date, patient):
    var = syd.find(db['Injection'], patient_id=patient['id'])
    min = np.abs(date - var[0]['date'])
    for tmp in var:
        if not tmp['date']:
            continue
        m = np.abs(date - tmp['date'])
        # if date < tmp['date']:
        #     tqdm.write(f'Injection {tmp["date"]} is after the wanted date {date}')

        if m <= min:
            min = m
            result = tmp
    return result


# -----------------------------------------------------------------------------
def guess_or_create_injection(db, ds, dicom_study, dicom_series):
    # EXAMPLE

    # (0040, 2017) Filler Order Number / Imaging Servi LO: 'IM00236518'
    # (0054, 0016)  Radiopharmaceutical Information Sequence   1 item(s) ----
    #  (0018, 0031) Radiopharmaceutical                 LO: 'Other'
    #  (0018, 1070) Radiopharmaceutical Route           LO: 'Intravenous route'
    #  (0018, 1072) Radiopharmaceutical Start Time      TM: '111200'
    #  (0018, 1074) Radionuclide Total Dose             DS: "98000000"
    #  (0018, 1075) Radionuclide Half Life              DS: "4062.599854"
    #  (0018, 1076) Radionuclide Positron Fraction      DS: "0.891"
    #  (0018, 1078) Radiopharmaceutical Start DateTime  DT: '20180926111208'
    #  (0054, 0300)  Radionuclide Code Sequence   1 item(s) ----
    #    (0008, 0100) Code Value                          SH: 'C-131A3'
    #    (0008, 0102) Coding Scheme Designator            SH: 'SRT'
    #    (0008, 0104) Code Meaning                        LO: '^68^Galium'

    # 1. try read Radiopharmaceutical Information Sequence
    # 2. Yes: read injection, info
    # 3. try to find one: rad, patient, date, total
    # 4. if no CREATE
    # else
    # try to find one: patient, date --> max delay few days

    try:
        # (0054, 0016) Radiopharmaceutical Information Sequence
        rad_seq = ds[0x0054, 0x0016]
        for rad in rad_seq:
            # (0018, 0031) Radiopharmaceutical
            rad_rad = rad[0x0018, 0x0031]
            rad_info = Box()
            # (0054, 0300) Radionuclide Code Sequence
            rad_code_seq = rad[0x0054, 0x0300]
            # (0018, 1074) Radionuclide Total Dose
            rad_info.total_dose = rad[0x0018, 0x1074].value
            #  (0018, 1076) Radionuclide Positron Fraction
            rad_info.positron_fraction = rad[0x0018, 0x1076].value
            rad_info.code = []
            rad_info.date = []
            for code in rad_code_seq:
                # (0008, 0104) Code Meaning
                rad_info.code.append(code[0x0008, 0x0104].value)
                # (0018, 1078) Radiopharmaceutical Start DateTime
                rad_info.date.append(rad[0x0018, 0x1078].value)
                injection = search_injection_from_info(db, dicom_study, rad_info)
            if not injection:
                injection = new_injection(db, dicom_study, rad_info)
    except:
        # tqdm.write('Cannot find info on radiopharmaceutical in DICOM')
        injection = search_injection(db, ds, dicom_study, dicom_series)

    # return injection (could be None)
    return injection


# -----------------------------------------------------------------------------
def search_injection_from_info(db, dicom_study, rad_info):
    patient_id = dicom_study.patient_id
    all_rad = syd.find(db['Radionuclide'])
    rad_names = [n.name for n in all_rad]

    if len(rad_info.code) != 1:
        tqdm.write('Error: several radionuclide found. Dont know what to do')
        return None

    # look for radionuclide name and date
    rad_code = rad_info.code[0]
    rad_date = datetime.strptime(rad_info.date[0], '%Y%m%d%H%M%S')
    s = [str_match(rad_code, n) for n in rad_names]
    s = np.array(s)
    i = np.argmax(s)
    rad_name = rad_names[i]

    # search if injections exist for this patient and this rad
    radionuclide = syd.find_one(db['Radionuclide'], name=rad_name)
    rad_info.radionuclide_id = radionuclide.id
    inj_candidates = syd.find(db['Injection'],
                              radionuclide_id=radionuclide.id,
                              patient_id=patient_id)
    if len(inj_candidates) == 0:
        return None

    # check date and activity
    max_time_days = timedelta(1.0)  # 1 day # FIXME  <------------------------ options
    found = None
    for ic in inj_candidates:
        d = ic.date
        if d > rad_date:
            t = d - rad_date
        else:
            t = rad_date - d
        if t <= max_time_days:
            act_diff = np.fabs(ic.activity_in_mbq - rad_info.total_dose)
            found = ic
            tqdm.write('Timedelta superior to 10 minutes')

    if found:
        tqdm.write(f'Injection found : {found}')
        return found
    else:
        return None


# -----------------------------------------------------------------------------
def search_injection(db, ds, dicom_study, dicom_series):
    patient_id = dicom_study.patient_id
    inj_candidates = syd.find(db['Injection'], patient_id=patient_id)
    dicom_date = dicom_series.acquisition_date

    # check date is before the dicom
    found = None
    for ic in inj_candidates:
        if not ic.date:
            continue
        if ic.date < dicom_date:
            if found:
                if ic.date > found.date:
                    found = ic
                    # tqdm.write('Several injections may be associated. Ignoring injection')
            else:
                found = ic

    if found:
        tqdm.write(f'Injection found : {found}')
        return found
    else:
        return None


# -----------------------------------------------------------------------------

### Modality and content_type ###
def guess_content_type(file):
    print(file)
    try:
        dicom = pydicom.read_file(str(file))
    except:
        dicom = None

    try:
        listmode = syd.check_type(file)
    except:
        listmode = None

    if dicom is not None:
        try:
            modality = dicom.Modality
        except:
            modality = None
            s = "Unknwon Modality"
            syd.raise_except(s)

        if modality is not None:
            try:
                tmp = dicom[0x0008, 0x103e].value
            except:
                tqdm.write('Cannot read Series Description')
            if modality == 'CT':
                if tmp.find('CT') != -1:
                    content_type = 'Tomo'
                else:
                    content_type = 'Other'

            elif modality == 'NM':
                if tmp.find('CE') != -1 or tmp.find('LIGHT') != -1 or tmp.find('THORAX') != -1:
                    content_type = 'Planar'
                elif tmp.find('TOMO TAP') != -1:
                    content_type = 'Proj'
                elif tmp.find('RECON') != -1:
                    content_type = 'Recon'
                else:
                    content_type = 'Other'
            elif modality == 'PT':
                if tmp.find('RECOM') != -1:
                    content_type = 'Recon'
                elif tmp.find('Transversal') != -1 or tmp.find('Rapport') != -1:
                    content_type = 'Other'
                else:
                    content_type = 'Tomo'

            elif modality == 'OT':
                if tmp.find('Volumetrix') != -1:
                    content_type = 'Recon'
                else:
                    content_type = 'Other'
            else:
                content_type = 'Other'

        else:
            s = f'Cannot read modality : {modality}'
            syd.raise_except(s)
    elif listmode is not None:
        if listmode != 'None.type':
            if listmode == 'Listmode.I':
                content_type = 'Listmode'
                modality = 'PT'
            else:
                mod = file.name.split('_')
                modality = 'NM'
                if mod[0] == 'tomo':
                    content_type = 'Proj'
                elif mod[0] == 'wb':
                    content_type = 'Planar'
                elif mod[0] == 'static':
                    content_type = 'Planar'
                else:
                    tqdm.write('Cannot read listmode content_type')
                    content_type = 'None'
        else:
            s = f"Unknwon Listmode file {file}"
            syd.raise_except(s)
    return modality, content_type


# -----------------------------------------------------------------------------

def guess_fov(db, acquisition):
    same_study = []
    same_modality = []
    same_date = []
    frame_of_reference_study = []
    same_for_dicom = []
    study = syd.find(db['DicomSeries'], acquisition_id=acquisition['id'])
    for s in study:  # Accessing the frame of reference uid directly from the file for all dicom in the acquisition
        frame_of_reference_study.append(s['frame_of_reference_uid'])


    acq = syd.find(db['Acquisition'], injection_id=acquisition['injection_id'])
    acq = [i for i in acq if (acquisition['id'] != i['id'])]  # Removing the acquisition given in the parameter
    for a in acq:
        dicom_series = syd.find_one(db['DicomSeries'], acquisition_id=a['id'])
        if dicom_series is not None:
            try:
                if dicom_series['dicom_study_id'] == study[0]['dicom_study_id']:
                    same_study.append(a)
            except:
                continue
    for a in same_study:
        if acquisition['modality'] == a['modality']:
            same_modality.append(a)
    for a in same_modality:
        if np.abs(acquisition['date'] - a['date']) < timedelta(1.0 / 24.0):
            same_date.append(a)
    for a in same_date:
        dicom_series = syd.find(db['DicomSeries'], acquisition_id=a['id'])
        for d in dicom_series:
            if d['frame_of_reference_uid'] in frame_of_reference_study:  # taking the FOR from the dico
                same_for = a
                same_for_dicom.append(d)
                break  # stoping at the first dicom found

    for d in same_for_dicom:
        str = d['series_description']
        if str.find('FOV1') != -1 or str.find('FOV 1') != -1:
            acquisition['fov'] = 2
            syd.update_one(db['Acquisition'], acquisition)
            tqdm.write(f'Update of acquisition :{acquisition}')
            return {}
        elif str.find('FOV2') != -1 or str.find('FOV 2') != -1:
            acquisition['fov'] = 1
            syd.update_one(db['Acquisition'], acquisition)
            tqdm.write(f'Update of acquisition :{acquisition}')
            return {}
        elif str.find('MFOV') != -1:
            print('')
        else:
            s = f'Cannot update acquisition {acquisition}'
            syd.raise_except(s)


# -----------------------------------------------------------------------------
def guess_stitch(db, acquisition):
    if acquisition['fov'] == '1':
        tmp = syd.find(db['Acquisition'], fov='2')
    elif acquisition['fov'] == '2':
        tmp = syd.find(db['Acquisition'], fov='1')
    else:
        tqdm.write(f'Cannot determnied the fov of {acquisition}')
        return {}
    injection = syd.find_one(db['Injection'], id=acquisition['injection_id'])
    patient = syd.find_one(db['Patient'], id=injection['patient_id'])
    dicom1 = syd.find(db['DicomSeries'], acquisition_id=acquisition['id'])
    res = []
    epsilon = 0.1
    delta = timedelta(1.0 / 24.0 * 2.0)
    for t in tmp:
        diff = np.abs(t['date'] - acquisition['date'])
        if diff < delta:
            dicom2 = syd.find(db['DicomSeries'], acquisition_id=t['id'])
            max = 0.0
            for d1 in dicom1:
                for d2 in dicom2:
                    ratio = difflib.SequenceMatcher(None, d1['series_description'], d2['series_description']).ratio()
                    if max - ratio < epsilon:
                        max = ratio
                        r = [d1, d2]
                res.append(r)
    for r in res:
        image1 = syd.find_one(db['Image'], dicom_series_id=r[0]['id'])
        file1 = syd.find_one(db['File'], id=image1['file_mhd_id'])
        image2 = syd.find_one(db['Image'], dicom_series_id=r[1]['id'])
        file2 = syd.find_one(db['File'], id=image2['file_mhd_id'])
        path1 = os.path.join(db.absolute_data_folder,os.path.join(file1['folder'], file1['filename']))
        path2 = os.path.join(db.absolute_data_folder,os.path.join(file2['folder'], file2['filename']))
        im1 = itk.imread(path1)
        im2 = itk.imread(path2)
        result = sti.stitch_image(im1, im2, 2, 0)
        itk.imwrite(result,'./tmp.mhd')
        if acquisition['fov'] == '1':
            im = {'patient_id': patient['id'], 'injection_id': injection['id'], 'acquisition_id': acquisition['id'],
                  'pixel_type': 'float', 'pixel_unit': 'counts', 'modality': acquisition['modality'],
                  'frame_of_reference_uid': r[0]['frame_of_reference_uid'], 'acquisition_date': acquisition['date']}
        else:
            im = {'patient_id': patient['id'], 'injection_id': injection['id'], 'acquisition_id': tmp['id'],
                  'pixel_type': 'float', 'pixel_unit': 'counts', 'modality': tmp['modality'],
                  'frame_of_reference_uid': r[0]['frame_of_reference_uid'], 'acquisition_date': tmp['date']}
        e = syd.insert_write_new_image(db, im, itk.imread('./tmp.mhd'))
        os.remove('./tmp.mhd')
        os.remove('./tmp.raw')
    return res
