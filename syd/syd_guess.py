#!/usr/bin/env python3
import syd
from tqdm import tqdm
from datetime import datetime
from datetime import timedelta
from box import Box
import numpy as np
from .syd_helpers import *
import pydicom


### Patient ###
def guess_or_create_patient(db, ds):

    # tyy to retrieve patient from PatientID tag
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
def nearest_acquisition(db,modality,date,patient):
    injec = nearest_injection(db,date,patient)
    result = None
    try:
        acq = syd.find(db['Acquisition'], injection_id=injec['id'], modality = modality)
    except:
        tqdm.write('Cannot find acquisition')
    if acq != []:
        min = np.abs(date - acq[0]['date'])
        for tmp in acq:
            m = np.abs(date - tmp['date'])
            if m<= timedelta(1.0/24.0/60.0*1.0):
                # timedelta usefull for multiple listmode for example tomo + wholebody
                if m <= min:
                    min = m
                    result = tmp

    return result

# -----------------------------------------------------------------------------
def guess_or_create_acquisition(db, dicom_series, patient):

    try: #try to found or create acquisition
        acquisition_date = dicom_series.acquisition_date
        modality = dicom_series.modality
        injection = syd.nearest_injection(db, acquisition_date, patient)
        acquisition = nearest_acquisition(db,modality,acquisition_date,patient)
        if not acquisition:
            acquisition = new_acquisition(db,dicom_series,acquisition_date,injection)

        print(acquisition)
    except:
        s = 'No Acquisition found'
        syd.raise_except(s)
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
def new_acquisition(db,dicom_series,date,injection):
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
    injection.activity_in_mbq = rad_info.total_dose/1e6
    injection.date = datetime.strptime(rad_info.date[0], '%Y%m%d%H%M%S')

    syd.insert_one(db['Injection'], injection)
    tqdm.write(f'Insert new injection {injection}')
    return injection

# -----------------------------------------------------------------------------
def nearest_injection(db,date, patient):
    var=syd.find(db['Injection'], patient_id=patient['id'])
    min = np.abs(date - var[0]['date'])
    for tmp in var:
        m = np.abs(date - tmp['date'])
        if m <= min:
            min = m
            result = tmp
    return result

# -----------------------------------------------------------------------------
def guess_or_create_injection(db, ds, dicom_study, dicom_series):

    # EXAMPLE

    #(0040, 2017) Filler Order Number / Imaging Servi LO: 'IM00236518'
    #(0054, 0016)  Radiopharmaceutical Information Sequence   1 item(s) ----
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
        rad_seq = ds[0x0054,0x0016]
        for rad in rad_seq:
            # (0018, 0031) Radiopharmaceutical
            rad_rad = rad[0x0018, 0x0031]
            rad_info = Box()
            # (0054, 0300) Radionuclide Code Sequence
            rad_code_seq = rad[0x0054,0x0300]
            # (0018, 1074) Radionuclide Total Dose
            rad_info.total_dose = rad[0x0018,0x1074].value
            #  (0018, 1076) Radionuclide Positron Fraction
            rad_info.positron_fraction = rad[0x0018,0x1076].value
            rad_info.code = []
            rad_info.date = []
            for code in rad_code_seq:
                # (0008, 0104) Code Meaning
                rad_info.code.append(code[0x0008,0x0104].value)
                # (0018, 1078) Radiopharmaceutical Start DateTime
                rad_info.date.append(rad[0x0018,0x1078].value)
                injection = search_injection_from_info(db, dicom_study, rad_info)
            if not injection:
                injection = new_injection(db, dicom_study, rad_info)
    except:
        #tqdm.write('Cannot find info on radiopharmaceutical in DICOM')
        injection = search_injection(db, ds, dicom_study, dicom_series)

    # return injection (could be None)
    return injection

# -----------------------------------------------------------------------------
def search_injection_from_info(db, dicom_study, rad_info):

    patient_id = dicom_study.patient_id
    all_rad = syd.find(db['Radionuclide'])
    rad_names = [ n.name for n in all_rad]

    if len(rad_info.code) != 1:
        tqdm.write('Error: several radionuclide found. Dont know what to do')
        return None

    # look for radionuclide name and date
    rad_code = rad_info.code[0]
    rad_date = datetime.strptime(rad_info.date[0], '%Y%m%d%H%M%S')
    s = [str_match(rad_code,n) for n in rad_names]
    s = np.array(s)
    i= np.argmax(s)
    rad_name = rad_names[i]

    # search if injections exist for this patient and this rad
    radionuclide = syd.find_one(db['Radionuclide'], name = rad_name)
    rad_info.radionuclide_id = radionuclide.id
    inj_candidates = syd.find(db['Injection'],
                              radionuclide_id = radionuclide.id,
                              patient_id = patient_id)
    if len(inj_candidates) == 0:
        return None

    # check date and activity
    max_time_days = timedelta(1.0) # 1 day # FIXME  <------------------------ options
    found = None
    for ic in inj_candidates:
        d = ic.date
        if d>rad_date:
            t = d-rad_date
        else:
            t = rad_date-d
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
    inj_candidates = syd.find(db['Injection'], patient_id = patient_id)
    dicom_date = dicom_series.acquisition_date

    # check date is before the dicom
    found = None
    for ic in inj_candidates:
        if ic.date < dicom_date:
            if found:
                if ic.date > found.date:
                    found = ic
                    #tqdm.write('Several injections may be associated. Ignoring injection')
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
                if tmp.find('CT')!=-1:
                    content_type = 'Tomo'
                else:
                    content_type = 'Other'

            elif modality == 'NM' or modality == 'PT':
                if tmp.find('LB CE') != -1 or tmp.find('LIGHT') !=-1:
                    content_type = 'Planar'
                elif tmp.find('TOMO TAP') != -1:
                    content_type = 'Proj'
                elif tmp.find('RECON') !=-1:
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
                modality='PT'
            else:
                mod = file.name.split('_')
                modality = 'NM'
                if mod[0] == 'tomo':
                    content_type = 'Tomo'
                elif mod[0] == 'wb':
                    content_type = 'Planar'
                elif mod[0] == 'static':
                    content_type ='Planar '
                else:
                    tqdm.write('Cannot read listmode content_type')
                    content_type ='None'
        else:
            s = f"Unknwon Listmode file {file}"
            syd.raise_except(s)
    return modality, content_type