#!/usr/bin/env python3
import dataset
from datetime import datetime
import syd


# -----------------------------------------------------------------------------
def create_acquisition_table(db):
    '''
    Create Acquisition table
    '''

    # create acquistion table
    q = 'CREATE TABLE Acquisition (\
    id INTEGER PRIMARY KEY NOT NULL,\
    injection_id INTEGER NOT NULL,\
    modality,\
    fov TEXT,\
    FOREIGN KEY(injection_id) REFERENCES Injection(id) on delete cascade\
    )'
    result = db.query(q)
    acquisition_table = db['acquisition']
    acquisition_table.create_column('date', db.types.datetime)


# -----------------------------------------------------------------------------
def find_acquisition(db, injection):
    acquisition = syd.find(db['Acquisition'], injection_id=injection['id'])
    acquisition = syd.sort_elements(acquisition, 'date')
    struct = []
    elements = []
    for tmp in acquisition:
        listmode = syd.find(db['Listmode'], acquisition_id=tmp['id'])
        dicom_series = syd.find(db['DicomSeries'], acquisition_id=tmp['id'])
        for d in dicom_series:
            dicom_struct = syd.find(db['DicomStruct'], dicom_series_id=d['id'])
            struct = struct + dicom_struct
        el = {'acquisition': tmp, 'listmode': listmode, 'dicom_serie': dicom_series, 'dicom_struct': struct}
        elements.append(el)
    return elements
