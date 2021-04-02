#!/usr/bin/env python3

import dataset
import sqlalchemy
import sqlite3
import json
import os
import sys
import datetime
from box import Box
from box import BoxList

from .syd_patient import *
from .syd_injection import *
from .syd_radionuclide import *
from .syd_listmode import *
from .syd_dicom import *
from .syd_file import *
from .syd_helpers import *
from .syd_image import *
from .syd_printformat import *
from .syd_acquisition import *
from .syd_view import *
from .syd_roi import *
from .syd_dose_by_organ import *

import logging

log = logging.getLogger()


# =============================================================================
# TODO        TODO           TODO           TODO
# rename get_complete_table_name -> guess_table_name with exception
# logger
# exception
# unit tests 
# =============================================================================


# -----------------------------------------------------------------------------
def create_db(filename, folder, overwrite=False):
    """
    Create a new database with given filename and folder.

    All default tables are created:
    - Info
    - Patient
    - Radionuclide
    - Injection
    - DicomStudy
    - DicomSerie
    - DicomFile
    - File
    - Image
    - Listmode
    - Acquisition
    - Roi
    - View
    - DoseByOrgan
    """

    # FIXME check if already exist
    if os.path.isdir(filename):
        raise RuntimeError(filename + ' is a directory')
    if os.path.isfile(filename):
        if overwrite:
            # print('Remove',filename)
            os.remove(filename)
        else:
            raise RuntimeError(filename + ' already exist')

    # create empty db
    db = dataset.connect('sqlite:///' + filename, engine_kwargs={'poolclass': sqlalchemy.pool.StaticPool})
    # conn = sqlite3.connect(filename)
    # c = conn.cursor()
    # c.execute('PRAGMA foreign_keys = ON')

    # DB meta info: creation date, filename, image folder
    db.create_table('Info')
    dbi = db['Info']
    dbi.create_column('creation_date', db.types.datetime)
    info = {
        'filename': filename,
        'creation_date': datetime.now(),
        'image_folder': folder
    }
    dbi.insert(info)

    # create Patient table
    create_printformat_table(db)
    create_patient_table(db)
    create_radionuclide_table(db)
    create_injection_table(db)
    create_file_table(db)
    create_dicom_study_table(db)
    create_dicom_series_table(db)
    create_dicom_file_table(db)
    create_image_table(db)
    create_listmode_table(db)
    create_acquisition_table(db)
    create_dicom_struct_table(db)
    create_roi_table(db)
    create_format_view_table(db)
    create_dose_table(db)
    insert_default_views(db)

    # insert all columns for all tables in printFormat
    insertFullPrintFormat(db)

    load_db_information(db, filename)

    return db


# -----------------------------------------------------------------------------
def insertFullPrintFormat(db):
    """
    Insert in PrintFormat table all columns for all tables of db
    """
    formats = []
    for table in db.tables:
        all_columns = ""
        for column in db[table].table.columns:
            all_columns += "{" + str(column)[len(table) + 1:] + "} "
        the_format = {"name": "full",
                      "table_name": table,
                      "format": all_columns}
        formats += [the_format]
    syd.insert(db["printformat"], formats)


# -----------------------------------------------------------------------------
def load_db_information(db, filename):
    # *NEEDED* to allow foreign keys
    q = 'PRAGMA foreign_keys = ON;'
    db.query(q)

    # add absolute filename in the database
    if os.path.isabs(filename):
        db.absolute_filename = filename
    else:
        db.absolute_filename = os.path.abspath(filename)

    # add absolute folder
    info = find_one(db['Info'], id=1)
    folder = info.image_folder
    db.absolute_data_folder = os.path.join(os.path.dirname(db.absolute_filename), folder)

    # add triggers
    set_file_triggers(db)
    # set_dicom_triggers(db) # not needed


# -----------------------------------------------------------------------------
def open_db(filename):
    """
    Open a return a sqlite db
    """

    # check if exist
    if os.path.isdir(filename):
        print('Error', filename, ' is a directory')
        exit(0)
    if not os.path.isfile(filename):
        print('Error', filename, 'does not exist')
        exit(0)

    # FIXME -> check data folder exist

    # connect to the db
    db = dataset.connect('sqlite:///' + filename, engine_kwargs={'poolclass': sqlalchemy.pool.StaticPool})

    load_db_information(db, filename)

    return db


# -----------------------------------------------------------------------------
def get_db_filename(filename):
    """
    If filename is empty, check the environment variable SYD_DB_FILENAME
    """

    # check if read filename from environment variable
    if filename == '':
        try:
            filename = os.environ['SYD_DB_FILENAME']
        except:
            s = 'Error, filename is empty and environment variable SYD_DB_FILENAME does not exist'
            raise_except(s)

    return filename


# -----------------------------------------------------------------------------
def insert(table, elements):
    """
    Insert all elements in the given table.
    Elements are given as vector of dictionary or a Box
    """

    if not isinstance(elements, list):
        s = "Error, elements is not an array. Maybe use 'syd.insert_one'"
        raise_except(s)

    try:
        with table.db as tx:
            for p in elements:
                p['_table_name_'] = table.name
                i = tx[table.name].insert(p)
                p['id'] = i
    except Exception as e:
        s = 'cannot insert element: {}\n'.format(p)
        s += str(e)
        raise_except(s)
    return elements


# -----------------------------------------------------------------------------
def insert_one(table, element):
    """
    Insert one single element in the table.
    """
    element['_table_name_'] = table.name
    elements = [element]
    e = insert(table, elements)
    return Box(e[0])


# -----------------------------------------------------------------------------
def delete_one(table, id):
    """
    Delete one element from the given table
    """

    delete(table, [id])


# -----------------------------------------------------------------------------
def delete(table, ids):
    """
    Delete several elements from the given table
    """

    if len(ids) == 0: return

    # Search for element
    e = find(table, id=ids)
    if len(e) != len(ids):
        s = 'Error, some elements with id={} do not exist in table {}'.format(ids, table.name)
        raise_except(s)

    # delete
    try:
        table.delete(id=ids)
    except Exception as e:
        s = 'Error, cannot delete element {} in table {} (maybe it is used in another table ?)\n'.format(ids,
                                                                                                         table.name)
        s += str(e)
        raise_except(s)


# -----------------------------------------------------------------------------
def update_one(table, element):
    """
    Update a single element according to the 'id'
    """

    e = syd.find_one(table, id=element['id'])
    if e == None:
        s = f'Error cannot update_one table {table.name}, the id is not found \n Element is {element}'
        raise_except(s)

    try:
        table.update(element, ['id'])  ##FIXME
    except:
        s = f'Error while updating table {table.name}, type issue ? \n Element is {element}'
        raise_except(s)


# -----------------------------------------------------------------------------
def update(table, elements):
    """
    Update all elements according to the 'id'
    """

    try:
        with table.db as tx:
            for e in elements:
                tx[table.name].update(e, ['id'])
    except:
        s = 'Error while updating {}, id not found ?'.format(elements)
        raise_except(s)


# -----------------------------------------------------------------------------
def find_one(table, **kwargs):
    """
    Retrieve one element from query
    """
    elem = table.find_one(**kwargs)
    if not elem:
        return None
    return Box(elem)


# -----------------------------------------------------------------------------
def find(table, **kwargs):
    """
    Retrieve elements from query. See module Dataset for query.
    Example: syd.find(db['Patient'], name='toto')
    """
    elem = table.find(**kwargs)
    elements = []
    for e in elem:
        elements.append(Box(e))

    return elements


# -----------------------------------------------------------------------------
def find_all(table):
    """
    Retrieve all elements
    """
    elem = table.all()
    elements = []
    for e in elem:
        elements.append(Box(e))

    return elements


# -----------------------------------------------------------------------------
def find_join_one(element, table, field_id):
    """
    Retrieve the join element with id = field_id
    """
    if not element:
        return None
    if field_id in element:
        id = element[field_id]
    else:
        return None
    elem = syd.find_one(table, id=id)
    if not elem:
        return None
    return Box(elem)


# -----------------------------------------------------------------------------
def sort_elements(elements, sorting_key):
    """
    Sort elements list according to the given field
    """
    try:
        elements = sorted(elements, key=lambda i: i[sorting_key])
    except:
        s = "Cannot sort by '" + sorting_key + "'. Using default sort."
        syd.warning(s)

    return elements


# -----------------------------------------------------------------------------
def get_complete_table_name(db, table_name):
    """
    Try to guess the table from the given name, retrieve the real table name if exist
    """
    tname = syd.guess_table_name(db, table_name)
    if not tname:
        print('Table {} does not exist. Tables: {}'.format(table_name, db.tables))
        exit(0)
    table_name = tname
    return table_name


# -----------------------------------------------------------------------------
def count(db, table_name):
    """
    Return the number of elements in the tables
    (not really useful)
    """
    return db[table_name].count()
