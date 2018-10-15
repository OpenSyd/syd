#!/usr/bin/env python3

import dataset
import json
import os
import sys
import datetime

# -----------------------------------------------------------------------------
def create_db(filename):
    '''
    Create a new DB

    Tables:
    - Info
    - Patient
    - Injection
    '''

    # FIXME check if already exist
    if (os.path.isdir(filename)):
        print('Error', filename, ' is a directory')
        exit
    if (os.path.isfile(filename)):
        print('Remove',filename)
        os.remove(filename)

    # create empty db
    db = dataset.connect('sqlite:///'+filename)

    # DB meta info: creation date, filename, image folder
    db.create_table('Info')
    dbi = db['Info']
    dbi.create_column('creation_date', db.types.datetime)
    info = {
        'filename': filename,
        'creation_date': datetime.datetime.now(),
        'image_folder': 'data'
    }
    dbi.insert(info)

    # create default tables
    q = 'CREATE TABLE Patient (\
    id INTEGER PRIMARY KEY NOT NULL,\
    study_id INTEGER NOT NULL UNIQUE,\
    name TEXT NOT NULL UNIQUE,\
    dicom_id TEXT UNIQUE,\
    sex TEXT)'
    result = db.query(q)

    # alternative # FIXME how to set unique ?
    '''p = db.create_table('Patient')
    p.create_column('name', type=db.types.text)
    p.create_column('study_id', type=db.types.integer)
    p.create_column('dicom_id', type=db.types.text)
    p.create_column('sex', type=db.types.text)
    '''

    # create default tables
    q = 'CREATE TABLE Injection (\
    id INTEGER PRIMARY KEY NOT NULL,\
    patient_id INTEGER NOT NULL,\
    radionuclide_id INTEGER NOT NULL,\
    activity_in_MBq REAL NO NULL)'
    result = db.query(q)
    injection_table = db['Injection']
    injection_table.create_column('date', db.types.datetime)
    injection_table.create_column('calibration_date', db.types.datetime)
    injection_table.create_column('calibration_activity_in_MBq', db.types.float)

    return db

# -----------------------------------------------------------------------------
def open_db(filename):
    '''
    Open a return a sqlite db
    '''

    # check if exist
    if (os.path.isdir(filename)):
        print('Error', filename, ' is a directory')
        exit(0)
    if (not os.path.isfile(filename)):
        print('Error', filename, 'does not exist')
        exit(0)

    # FIXME -> check data folder exist

    # connect to the empty db
    db = dataset.connect('sqlite:///'+filename)

    return db

# -----------------------------------------------------------------------------
def get_db_filename(filename):
    '''
    Check environment variable SYD_DB_FILENAME if filename is void
    '''

    # check if read filename from environment variable
    if (filename == ''):
        try:
            filename = os.environ['SYD_DB_FILENAME']
        except:
            print('Error, filename is empty and environment variable SYD_DB_FILENAME does not exist')
            exit(0)

    return filename

