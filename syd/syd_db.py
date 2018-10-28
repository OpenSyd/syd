#!/usr/bin/env python3

import dataset
import sqlite3
import json
import os
import sys
import datetime

from .syd_patient import *
from .syd_injection import *
from .syd_radionuclide import *
from .syd_dicom import *
from .syd_file import *
from .syd_helpers import *
from .syd_image import *

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
    q = 'PRAGMA foreign_keys = ON;'
    db.query(q)
    # conn = sqlite3.connect(filename)
    # c = conn.cursor()
    # c.execute('PRAGMA foreign_keys = ON')

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
    create_dicom_serie_table(db)
    create_dicom_file_table(db)
    create_file_table(db)
    create_image_table(db)

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

    # connect to the db
    db = dataset.connect('sqlite:///'+filename)

    # *NEEDED* to allow foreign keys
    q = 'PRAGMA foreign_keys = ON;'
    db.query(q)

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
            s = 'Error, filename is empty and environment variable SYD_DB_FILENAME does not exist'
            raise_except(s)

    return filename


# -----------------------------------------------------------------------------
def insert(table, elements):
    '''
    Bulk insert all elements in the table.
    Elements are given as vector of dictionary
    '''
    ids = []
    try:
        with table.db as tx:
            for p in elements:
                i = tx[table.name].insert(p)
                ids.append(i)
    except Exception as e:
        s = 'cannot insert element: {}\n'.format(p)
        raise_except(s)
    return ids

# -----------------------------------------------------------------------------
def insert_one(table, element):
    '''
    Bulk insert one element in the table.
    '''
    elements = [element]
    ids = insert(table, elements)
    return ids[0]


# -----------------------------------------------------------------------------
def delete_one(table, id):
    '''
    Delete one element from the given table
    '''

    delete(table, [id])

# -----------------------------------------------------------------------------
def delete(table, ids):
    '''
    Delete one element from the given table
    '''

    if len(ids) == 0: return

    # Search for element
    e = table.find(id=ids)
    l = 0
    for ee in e: l = l+1
    if l != len(ids):
        s = 'Error, some elements with id={} do not exist in table {}'.format(ids, table.name)
        raise_except(s)

    # delete
    try:
        table.delete(id=ids)
    except Exception as e:
        s = 'Error, cannot delete element {} in table {} (maybe it is used in another table ?)'.format(ids, table.name)
        raise_except(s)


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
            s = 'Error, table {} has several elements with {}={}'.format(table.name, table_key_name, s)
            raise_except(s)
        element.pop(key_name)
        k = table.name.lower()+'_id'
        element[k] = row['id']
        i = i +1
    if (i ==0):
        s = 'Error, table {} does not contain element with {}={}'.format(table.name, table_key_name, s)
        raise_except(s)

    return element


# -----------------------------------------------------------------------------
def print_elements(table_name, print_format, elements):
    '''
    Pretty print some elements
    '''

    for e in elements:
        s = ' '.join(str(x) for x in e.values())
        print(s)

