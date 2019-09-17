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
    num INTEGER NOT NULL,\
    name TEXT NOT NULL,\
    dicom_id TEXT UNIQUE,\
    sex TEXT)'
    result = db.query(q)

    # alternative # FIXME how to set unique ?
    # p = db.create_table('Patient')
    # p.create_column('name', type=db.types.text)
    # p.create_column('num', type=db.types.integer)
    # p.create_column('dicom_id', type=db.types.text)
    # p.create_column('sex', type=db.types.text)

# -----------------------------------------------------------------------------
def print_patient(print_format, elements):
    print(print_format, elements)

    # trial (work in progress)
    s = ''
    for e in elements:
        s = s + '{id:>3} {num:>3} {name:>15} {dicom_id}\n'.format(id=e['id'],
                                                                       num=e['num'],
                                                                       dicom_id=e['dicom_id'],
                                                                       name=e['name'])
    print(s)

