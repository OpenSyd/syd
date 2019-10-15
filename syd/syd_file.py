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
    folder TEXT NOT NULL,\
    filename TEXT NOT NULL,\
    md5 TEXT)'
    result = db.query(q)

    # define trigger
    con = db.engine.connect()
    cur = con.connection.cursor()
    cur.execute("CREATE TRIGGER on_file_delete AFTER DELETE ON File BEGIN\
    SELECT * FROM Info; \
    SELECT file_on_delete(OLD.folder, OLD.filename);\
    END;")
    con.close()


# -----------------------------------------------------------------------------
def file_on_delete(db, folder, filename):
    f = {}
    f['folder'] = folder
    f['filename'] = filename
    p = get_file_absolute_filename(db, f)
    print('Deleting file', p)
    os.remove(p)


# -----------------------------------------------------------------------------
def set_file_triggers(db):
    con = db.engine.connect()
    # embed the db
    def t(folder, filename):
        file_on_delete(db, folder, filename)
    con.connection.create_function("file_on_delete", 2, t)


# -----------------------------------------------------------------------------
def get_file_absolute_filename(db, fi):
    '''
    Return the absolute file path of the given file
    '''
    p = os.path.join(db.absolute_data_folder, fi.folder)
    p = os.path.join(p, fi.filename)
    return p


# -----------------------------------------------------------------------------
def new_file():
    '''
    Create and return a new file
    '''
    return new_file('not_yet', 'not_yet')


# -----------------------------------------------------------------------------
def new_file(db, folder, filename):
    '''
    Create and return a new file
    '''
    info = { 'folder':folder, 'filename': filename}
    file = syd.insert_one(db['File'], info)
    return file


