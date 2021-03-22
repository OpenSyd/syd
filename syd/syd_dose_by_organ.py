#!/usr/bin/env python3

import syd
from box import Box


# -----------------------------------------------------------------------------
def create_dose_table(db):
    '''
    Create Dose by Organ table
    '''
    q = 'CREATE TABLE DoseByOrgan (\
    id INTEGER PRIMARY KEY NOT NULL,\
    id_injection INTEGER NOT NULL,\
    id_roi INTEGER NOT NULL,\
    value TEXT,\
    units TEXT,\
    std_dev TEXT,\
    label TEXT,\
    FOREIGN_KEY(id_injection) REFERENCES Injection(id) on delete cascade,\
    FOREIGN_KEY(id_roi) REFERENCES Roi(id) on delete cascade\
    )'
    result = db.query(db)

# -----------------------------------------------------------------------------
