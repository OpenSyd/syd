#!/usr/bin/env python3

import dataset

# -----------------------------------------------------------------------------
def create_patient_table(db):
    '''
    Create the patient table
    '''

    # create Patient table
    q = 'CREATE TABLE Patient (\
    id INTEGER PRIMARY KEY NOT NULL,\
    study_id INTEGER NOT NULL UNIQUE,\
    name TEXT NOT NULL UNIQUE,\
    dicom_id TEXT UNIQUE,\
    sex TEXT)'
    result = db.query(q)

    # alternative # FIXME how to set unique ?
    # p = db.create_table('Patient')
    # p.create_column('name', type=db.types.text)
    # p.create_column('study_id', type=db.types.integer)
    # p.create_column('dicom_id', type=db.types.text)
    # p.create_column('sex', type=db.types.text)

