#!/usr/bin/env python3

import dataset
import syd
from box import Box


# -----------------------------------------------------------------------------
def create_dose_table(db):
    '''
    Create Dose by Organ table
    '''
    q = 'CREATE TABLE DoseByOrgan (\
    id INTEGER PRIMARY KEY NOT NULL,\
    injection_id INTEGER NOT NULL,\
    roi_id INTEGER NOT NULL,\
    image_dose_id INTEGER,\
    value TEXT,\
    units TEXT,\
    std_dev TEXT,\
    FOREIGN KEY(injection_id) REFERENCES Injection(id) on delete cascade,\
    FOREIGN KEY(roi_id) REFERENCES Roi(id) on delete cascade\
    )'
    result = db.query(q)

# -----------------------------------------------------------------------------
