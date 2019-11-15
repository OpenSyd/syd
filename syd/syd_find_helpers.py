#!/usr/bin/env python3

import syd

# -----------------------------------------------------------------------------
def find_patient(db, patient_name):

    patient = syd.find_one(db['Patient'], name = patient_name)
    if patient == None:
        s = f'Cannot find patient with name {patient_name}'
        syd.raise_except(s)

    return patient
    

# -----------------------------------------------------------------------------
def find_series(db, patient_id, grep):

    # select study from this patient
    studies = syd.find(db['DicomStudy'], patient_id = patient_id)
    study_ids = [s.id for s in studies]

    # series
    elements = syd.find(db['DicomSeries'], dicom_study_id=study_ids)
    
    # select series
    grep.append('%ignore')
    elements, s = syd.grep(db, 'DicomSeries', elements, grep=grep)

    return elements, s

# -----------------------------------------------------------------------------
def find_images(db, patient_id, grep):

    elements = syd.find(db['Image'], patient_id = patient_id)
    elements, s = syd.grep(db, 'Image', elements, grep=grep)

    return elements, s


