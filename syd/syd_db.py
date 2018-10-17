#!/usr/bin/env python3

import dataset
import json
import os
import sys
import datetime
from .syd_patient import *
from .syd_injection import *
from .syd_radionuclide import *

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

    # create Patient table
    create_patient_table(db)
    create_radionuclide_table(db)
    create_injection_table(db)

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

# -----------------------------------------------------------------------------
def insert(table, elements):
    '''
    Bulk insert all elements in the table.
    Elements are given as vector of dictionary
    '''
    with table.db as tx:
        for p in elements:
            tx[table.name].insert(p)



# -----------------------------------------------------------------------------
def replace_key_with_id(element, key_name, table, table_key_name):
    '''
    Replace the key 'key_name' in the element (dict) with the id of the
    element find in the table
    '''
    #p = table.find_one(table_key_name=element[key_name])
    statement = 'SELECT id FROM '+table.name+' WHERE '+table_key_name+' = "'+element[key_name]+'"'
    i = 0
    s = element[key_name]
    res = table.db.query(statement)
    for row in res:
        if (i != 0):
            print('Error, table {} has several elements with {}={}'
                  .format(table.name, table_key_name, s))
            exit(0)
        element.pop(key_name)
        k = table.name.lower()+'_id'
        element[k] = row['id']
        i = i +1
    if (i ==0):
        print('Error, table {} does not contain element with {}={}'
              .format(table.name, table_key_name, s))
        exit(0)

    return element
