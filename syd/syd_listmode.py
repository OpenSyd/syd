#!/usr/bin/env python3

import dataset
import os
from pathlib import Path
import numpy as np
from tqdm import tqdm
from .syd_db import *
from .syd_helpers import *
from datetime import timedelta
from datetime import datetime
from shutil import copy
import re
import pydicom


# -----------------------------------------------------------------------------
def create_listmode_table(db):
    '''
    Create Listmode table
    '''

    # create Listmode table
    q = 'CREATE TABLE Listmode (\
	id INTEGER PRIMARY KEY NOT NULL,\
	injection_id INTEGER NOT NULL,\
	FOREIGN KEY(injection_id) REFERENCES Injection(id) on delete cascade\
	)'
    result = db.query(q)


# -----------------------------------------------------------------------------
def create_listmode_file_table(db):
    '''
    Create ListmodeFile table
    '''
    q = 'CREATE TABLE ListmodeFile (\
     id INTEGER PRIMARY KEY NOT NULL,\
     listmode_id INTEGER NOT NULL,\
     file TEXT,\
     info TEXT,\
     type TEXT,\
     FOREIGN KEY(listmode_id) REFERENCES Listmode(id) on delete cascade\)'
    result = db.query(q)


# -----------------------------------------------------------------------------
def insert_listmode_from_file(db, filepath, injection):
    '''
    Insert or update a listmode from a filepath
    '''
    var = list(Path(filepath).rglob("*"))
    tqdm.write('Found {} files/folders in {}'.format(len(var), var))
    pbar=tqdm(total=len(var), leave=False)
    max_time_days = timedelta(1.0)
    pattern = re.compile("I\d\d")
    for x in var:
        tmp = x
        x = str(x.name)
        try:
            injec = syd.find(db['Injection'], patient_id=injection['patient_id'])
        except:
            tqdm.write('Ignoring {}: cannot find corresponding injection'.format(x))
            return {}
        if x.endswith(".dat"):
            date = return_date(x)
            d = injection['date']
            if d > date:
                continue
            elif (date - d < max_time_days):
                listmode = {'injection_id': injection['id']}
                try:
                    syd.insert_one(db['Listmode'], listmode)
                except:
                    print('Failure to insert Listmode')
                    return {}
                patient = syd.find_one(db['Patient'], id=injection['patient_id'])
                date_reduite = date.__format__('%Y-%m-%d')
                tmp = os.path.join(db.absolute_data_folder, patient['name'])
                path = os.path.join(tmp, date_reduite)
                folder = os.path.join(path, 'listMode')
                folder_spect = os.path.join(folder, 'spect')
                if not os.path.exists(folder):
                    os.makedirs(folder)
                if not os.path.exists(folder_spect):
                    os.makedirs(folder_spect)
                l = syd.find_one(db['Listmode'], injection_id=injection['id'])
                listmode_file = {'listmode_id': l.id, 'file': os.path.join(folder_spect, x),
                                 'type': 'listmode spect'}
                try:
                    syd.insert_one(db['ListmodeFile'], listmode_file)
                except:
                    print('Failure to insert Listmode file')
                    return {}
                filename = os.path.join(filepath, x)
                copy(filename, folder_spect)
            pbar.update(1)

        elif pattern.match(x):
            try:
                ds = pydicom.read_file(str(tmp))
            except:
                tqdm.write('Ignoring {}: not a listmode'.format(Path(x).name))
                return {}
            date = return_date_str(ds[0x0008, 0x002a].value)
            # for ic in injec:
            d = injection['date']
            if d > date:
                continue
            elif (date - d < max_time_days):
                listmode = {'injection_id': injection['id']}
                try:
                    syd.insert_one(db['Listmode'], listmode)
                except:
                    print('Failure to insert Listmode')
                patient = syd.find_one(db['Patient'], id=injection['patient_id'])
                date_reduite = date.__format__('%Y-%m-%d')
                tmp_path = os.path.join(db.absolute_data_folder, patient['name'])
                path = os.path.join(tmp_path, date_reduite)
                folder = os.path.join(path, 'listMode')
                folder_pet = os.path.join(folder, 'pet')
                if not os.path.exists(folder):
                    os.makedirs(folder)
                if not os.path.exists(folder_pet):
                    os.makedirs(folder_pet)
                l = syd.find_one(db['Listmode'], injection_id=injection['id'])
                listmode_file = {'listmode_id': l.id, 'file': os.path.join(folder_pet, x),
                                 'type': 'listmode pet'}
                try:
                    syd.insert_one(db['ListmodeFile'], listmode_file)
                except:
                    print('Failure to insert Listmode File')
                copy(tmp, folder_pet)
            pbar.update(1)
    pbar.close()


# -----------------------------------------------------------------------------
def return_date(filename):
    try:
        date = filename.split(".")[8]
        annee = ['2017', '2018', '2019', '2020', '2021', '2022']
        for a in annee:
            if date.find(a) != -1:
                return datetime.strptime(date[0:date.find(a) + 8], '%d%m%Y%H%M')
    except:
        print('Filename not long enough')
        return(datetime(1958,10,4,0,0,0))


# -----------------------------------------------------------------------------
def return_date_str(var_str):
    annee = ['2017', '2018', '2019', '2020', '2021', '2022']
    for a in annee:
        if var_str.find(a) != -1:
            return datetime.strptime(var_str[0:var_str.find(a) + 14], '%Y%m%d%H%M%S')
