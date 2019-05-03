#!/usr/bin/env python3

import dataset
import syd


# -----------------------------------------------------------------------------
def create_printformat_table(db):
    '''
    Create the printformat table
    '''

    # create Patient table
    q = 'CREATE TABLE PrintFormat (\
    id INTEGER PRIMARY KEY NOT NULL,\
    name TEXT NOT NULL,\
    table_name TEXT NOT NULL,\
    format TEXT)'

    result = db.query(q)

    # insert default elements
    r = [
        { 'name': 'default', 'table_name': 'Patient',
          'format': '{id:3} {study_id:3} {name: <20} {dicom_id: <10}' },

        { 'name': 'default', 'table_name': 'Radionuclide',
          'format': '{id:3} {name: <10} {element: <12} {atomic_number:4d} {mass_number:4d} {metastable:2} {half_life_in_hours:8.2f} {max_beta_minus_energy_in_kev:8.2f}\n' },

        { 'name': 'default', 'table_name': 'Injection',
          'format': '{id:4} [{patient_id}] {patient.name:<5} {radionuclide.name:5} {activity_in_MBq:8.2f} MBq  {date:%Y-%m-%d %H:%M}\n'
        },

        { 'name': 'default', 'table_name': 'DicomSerie',
          'format': '{id:4} [{patient_id}] {patient.name:<5} {modality} {acquisition_date:%Y-%m-%d %H:%M} {series_description} / {study_description} / {study_name} / {dataset_name} \n'
        },
        
        { 'name': 'file', 'table_name': 'DicomSerie',
          'format': '{id:4} {filename} \n'
        },
        
    ]       

    syd.insert(db['PrintFormat'], r)
