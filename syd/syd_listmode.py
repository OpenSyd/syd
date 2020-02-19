#!/usr/bin/env python3

import dataset
import re
from datetime import datetime
from datetime import timedelta
from pathlib import Path
import syd
import glob
import numpy as np
from box import Box
import pydicom
import os
from shutil import copy
from tqdm import tqdm


# -----------------------------------------------------------------------------
def create_listmode_table(db):
    '''
    Create Listmode table
    '''
    q = 'CREATE TABLE Listmode (\
     id INTEGER PRIMARY KEY NOT NULL,\
     acquisition_id INTEGER NOT NULL,\
     file_id INTEGER UNIQUE,\
     FOREIGN KEY (file_id) REFERENCES File (id) on delete cascade,\
     FOREIGN KEY(acquisition_id) REFERENCES Acquisition(id) on delete cascade\
     )'
    result = db.query(q)
    listmode_table = db['Listmode']
    listmode_table.create_column('date', db.types.datetime)

    # define trigger
    con = db.engine.connect()
    cur = con.connection.cursor()
    cur.execute('CREATE TRIGGER on_listmode_delete AFTER DELETE ON Listmode\
    BEGIN\
    DELETE FROM File WHERE id = OLD.file_id;\
    END;')
    con.close()

# -----------------------------------------------------------------------------
def on_listmode_delete(db, x):
    # NOT really used. Kept here for example and display delete message
    print('Delete Listmode ', x)


# -----------------------------------------------------------------------------
def set_listmode_triggers(db):
    con = db.engine.connect()
    def t(x):
        on_listmode_delete(db, x)

    con.connection.create_function("on_listmode_delete", 1, t)

# -----------------------------------------------------------------------------
def insert_listmode_from_folder(db,folder,patient):
    files = list(Path(folder).rglob('*'))
    tqdm.write('Found {} files/folders in {}'.format(len(files), folder))

    pbar = tqdm(total=len(files), leave=False)
    for f in files:
        insert_listmode_from_file(db, f, patient)
        pbar.update(1)

    pbar.close()
# -----------------------------------------------------------------------------
def insert_listmode_from_file(db, filename, patient):
    patient_folder = os.path.join(db.absolute_data_folder, patient['name'])
    e = check_type(filename)
    ftype, end = e.split('.')
    if ftype == 'Listmode':
        print('')
        if end == 'dat':
            date = return_date(filename.name)
            modality = 'NM'
        elif end == 'I':
            ds = pydicom.read_file(str(filename))
            try:
                acquisition_date = ds.AcquisitionDate
                acquisition_time = ds.AcquisitionTime
                date = syd.dcm_str_to_date(acquisition_date+acquisition_time)
            except:
                date = return_date_str(ds[0x0008, 0x002a].value)
            modality = 'PT'
        else:
            tqdm.write('Date not found on DICOM')
            return 1

        # Check if the listmode is already in the file with date and name
        listmode = syd.find(db['Listmode'], date=date)
        if listmode is not None:
            for l in listmode:
                file = syd.find_one(db['File'], id=l['file_id'])
                if file['filename'].find(filename.name) != -1:
                    tqdm.write('Ignoring {} : Listmode already in the db'.format(filename))
                    return {}

        # Check if the acquisition exists or not
        res = check_acquisition(db, date, patient)
        if res is not None: #When an acquisition is found
            a1 = res
        else:  # Creation of the acquisition if it does not exist
            d1 = nearest_injection(db, date, patient)
            a0 = {'injection_id': d1['id'], 'modality': modality, 'date': date}
            syd.insert_one(db['Acquisition'], a0)
            a1 = syd.find_one(db['Acquisition'], date=a0['date'])
        tqdm.write('Acquisition : {}'.format(a1))
        # Listmode creation then insertion
        l0 = {'acquisition_id': a1['id'], 'date':date}
        syd.insert_one(db['Listmode'], l0)
        l1 = syd.find(db['Listmode'], acquisition_id=a1['id'])
        acqui_folder = os.path.join(patient_folder, 'acqui_' + str(a1['id']))
        base_filename = 'LM_' + str(l1[len(l1) - 1]['id']) + '_' + str(filename.name)
        if not os.path.exists(acqui_folder):
            os.makedirs(acqui_folder)
        # File creation for the file table
        afile = Box()
        afile.folder = acqui_folder
        afile.filename = base_filename
        syd.insert_one(db['File'], afile)
        # Update of listmode to account for the file_id
        f0 = syd.find_one(db['File'], filename=afile.filename)
        l2 = {'id': l1[len(l1) - 1]['id'], 'acquisition_id': a1['id'], 'file_id': f0['id']}
        syd.update_one(db['Listmode'], l2)
        # Moving the file
        copy(filename, acqui_folder)
        old_filename = os.path.join(acqui_folder, filename.name)
        new_filename = os.path.join(acqui_folder, base_filename)
        os.rename(old_filename, new_filename)

    else:
        tqdm.write('Ignoring {}: it is not a Listmode'.format(filename))


# -----------------------------------------------------------------------------
def check_type(file):
    file=str(file.name)
    pattern = re.compile("I\d\d")
    if file.endswith(".dat"):
        if file == "fullPatientDetails.dat":
            result = "None.type"
        else:
            result = "Listmode.dat"
    elif file.endswith(".list"):
        result = "Listmode.list"
    elif file.endswith(".npz"):
        result = "Listmode.npz"
    elif pattern.match(file):
        result = "Listmode.I"
    else:
        result = "None.Type"

    return result

# -----------------------------------------------------------------------------
def check_acquisition(db,date,patient):
    injec = nearest_injection(db,date,patient)
    result = None
    try:
        acq = syd.find(db['Acquisition'], injection_id=injec['id'])
    except:
        tqdm.write('Cannot find acquisition')
    if acq != []:
        min = np.abs(date - acq[0]['date'])
        for tmp in acq:
            m = np.abs(date - tmp['date'])
            if m<= timedelta(1.0/24.0/60.0*15.0):
                if m <= min:
                    min = m
                    result = tmp


    return result
# -----------------------------------------------------------------------------
def return_date(filename):
    try:
        date = filename.split(".")[8]
        annee = ['2017', '2018', '2019', '2020', '2021', '2022']
        for a in annee:
            if date.find(a) != -1:
                return datetime.strptime(date[0:date.find(a) + 10], '%d%m%Y%H%M%S')
    except:
        print('Filename not long enough')
        return datetime(1958, 10, 4, 0, 0, 0)


# -----------------------------------------------------------------------------
def return_date_str(var_str):
    annee = ['2017', '2018', '2019', '2020', '2021', '2022']
    for a in annee:
        if var_str.find(a) != -1:
            return datetime.strptime(var_str[0:var_str.find(a) + 14], '%Y%m%d%H%M%S')

# -----------------------------------------------------------------------------
def nearest_injection(db,date, patient):
    var=syd.find(db['Injection'], patient_id=patient['id'])
    min = np.abs(date - var[0]['date'])
    for tmp in var:
        m = np.abs(date - tmp['date'])
        if m <= min:
            min = m
            result = tmp
    return result
