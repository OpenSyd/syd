#!/usr/bin/env python3

import dataset

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
