#!/usr/bin/env python3

import dataset

# -----------------------------------------------------------------------------
def create_injection_table(db):
    '''
    Create the injection table
    '''

    # create Injection table
    q = 'CREATE TABLE Injection (\
    id INTEGER PRIMARY KEY NOT NULL,\
    patient_id INTEGER NOT NULL,\
    radionuclide_id INTEGER NOT NULL,\
    activity_in_MBq REAL,\
    FOREIGN KEY(patient_id) REFERENCES Patient(id) on delete cascade\
    FOREIGN KEY(radionuclide_id) REFERENCES Radionuclide(id)\
    )'
    result = db.query(q)
    injection_table = db['Injection']
    injection_table.create_column('date', db.types.datetime)
    injection_table.create_column('calibration_date', db.types.datetime)
    injection_table.create_column('calibration_activity_in_MBq', db.types.float)
