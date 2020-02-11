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
    sorting_key TEXT,\
    table_name TEXT NOT NULL,\
    format TEXT)'

    result = db.query(q)
    insert_default_printformat_elements(db)

# -----------------------------------------------------------------------------
def insert_default_printformat_elements(db):
    # insert default elements
    r = [
        
        { 'name': 'default', 'table_name': 'Patient',
          'format': '{id:3} {num:3} {name: <20} {dicom_id: <10} {labels}' },
        
        { 'name': 'default', 'sorting_key': 'atomic_number', 'table_name': 'Radionuclide',
          'format': '{id:3} {name: <10} {element: <12} {atomic_number:4d} {mass_number:4d} {metastable:2} {half_life_in_hours:8.2f} {max_beta_minus_energy_in_kev:8.2f}  {labels}' },
        
        { 'name': 'default', 'sorting_key': 'date', 'table_name': 'Injection',
          'format': '{id:4} [{patient_id}] {patient.name:<5} {radionuclide.name:5} {activity_in_mbq:8.2f} MBq  {date:%Y-%m-%d %H:%M} {cycle} {labels}'
        },

        { 'name': 'default', 'table_name': 'DicomStudy',
          'format': '{id:4} {patient.name:<5} {study_description} / {study_name}  {labels}'
        },
        
        { 'name': 'default', 'sorting_key': 'acquisition_date', 'table_name': 'DicomSeries',
          'format': '{id:4} {dicom_study.patient.name: <10} {injection.radionuclide.name} {time_from_inj} {injection.cycle} {injection.activity_in_mbq} {modality} {acquisition_date:%Y-%m-%d-%H:%M} {image_size}x{nb_dicom_files} {image_spacing} / {series_description} / {dicom_study.study_description} / {dicom_study.study_name} / {dataset_name} / {labels}'
        },
        
        { 'name': 'file', 'sorting_key': 'date', 'table_name': 'DicomSeries',
          'format': '{id:4} {dicom_study.patient.name: <10} {abs_filename} {labels} '
        },
        
        { 'name': 'default', 'table_name': 'DicomFile',
          'format': '{id:4} {file_id} {dicom_series.dicom_study.patient.name} {instance_number} {sop_uid} {abs_filename}  {labels} '
        },
        
        { 'name': 'default', 'table_name': 'File',
          'format': '{id:4} {folder} {filename} {labels}'
        },

        { 'name': 'file', 'table_name': 'File',
          'format': '{id:4} {absolute_filename}  {labels}'
        },

        { 'name': 'file', 'table_name': 'Image',
          'format': '{id:4} {abs_filename}  {labels}'
        },

        { 'name': 'default', 'sorting_key': 'acquisition_date', 'table_name': 'Image',
          'format': '{id:4} {patient.name:<5} {modality} {acquisition_date:%Y-%m-%d-%H:%M}  {time_from_inj} {injection.radionuclide.name:5} {injection.date:%Y-%m-%d-%H:%M}  {dicom_series_id} {pixel_type} {pixel_unit} {dicom_series.series_description} / {dicom_series.dicom_study.study_description} / {dicom_series.dicom_study.study_name} / {dicom_series.dataset_name}  {labels} '
        },

        {'name': 'default', 'table_name': 'Listmode',
         'format': '{id:4} [{injection_id}]  {labels}'
         },

        {'name': 'default', 'table_name': 'ListmodeFile',
         'format': '{id:4} [{listmode_id}] {file} {info} {type} {labels}'
         },

        { 'name': 'file', 'table_name': 'PrintFormat',
          'format': '{id:4} {name} {table_name} {format})  {labels}'
        },
        
    ]       

    syd.insert(db['PrintFormat'], r)

