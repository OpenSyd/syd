#!/usr/bin/env python3

import dataset
import os
from .syd_db import *

# -----------------------------------------------------------------------------
def create_file_table(db):
    '''
    Create the file table
    '''
    # create File table
    q = 'CREATE TABLE File (\
    id INTEGER PRIMARY KEY NOT NULL,\
    path TEXT NOT NULL,\
    filename TEXT NOT NULL,\
    md5 TEXT)'
    result = db.query(q)


# -----------------------------------------------------------------------------
def get_file_absolute_filename(db, id):
    '''
    Return the absolute file path of the give file id
    '''
    f = db['File'].find_one(id=id)
    p = os.path.join(db.absolute_data_folder, f['path'])
    p = os.path.join(p, f['filename'])
    return p


# -----------------------------------------------------------------------------
def new_file():
    '''
    Create and return a new file
    '''
    return new_file('not_yet', 'not_yet')

# -----------------------------------------------------------------------------
def new_file(db, path, filename):
    '''
    Create and return a new file
    '''
    info = { 'path':path, 'filename': filename}
    file = syd.insert_one(db['File'], info)
    return file


