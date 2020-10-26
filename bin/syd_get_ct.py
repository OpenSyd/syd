#!/usr/bin/env python3

import syd
import click
import pydicom

# ------------------------------------------------------------------
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('dicom_id')
@click.option('--db', default='', help='DB filename (SYD_DB_FILENAME environment variable is used if no filename')
@click.option('--struct', '-s', default=False, is_flag=True, help='Only if the id is a DicomStruct id in SYD')
def nm2ct(db, dicom_id, struct):
    """
    DICOM_ID : The id in a SYD database of the DicomSeries of a PET or a SPECT for the program to find the matching CT
    """
    res = []
    db_filename = syd.get_db_filename(db)
    db = syd.open_db(db_filename)
    db_folder = db.absolute_data_folder
    if struct:
        dicom_struct = syd.find_one(db['DicomStruct'], id=dicom_id)
        dicom_series = syd.find_one(db['DicomSeries'], id=dicom_struct['dicom_series_id'])
    else:
        dicom_series = syd.find_one(db['DicomSeries'], id=dicom_id)
    injection = syd.find_one(db['Injection'], id=dicom_series['injection_id'])
    patient = syd.find_one(db['Patient'], id=injection['patient_id'])
    dicom_file = syd.find_one(db['DicomFile'], dicom_series_id=dicom_series['id'])
    file = syd.find_one(db['File'], id=dicom_file['file_id'])
    path = db_folder + '/' + file['folder'] + '/' + file['filename']
    ds = pydicom.read_file(path)
    instance_uid = ds[0x0020, 0x000d].value
    frame_uid = ds[0x0020, 0x0052].value
    injections = syd.find(db['Injection'], patient_id=patient['id'])
    for i in injections:
        dicoms = syd.find(db['DicomSeries'], injection_id=i['id'])
        for d in dicoms:
            df = syd.find_one(db['DicomFile'], dicom_series_id=d['id'])
            f = syd.find_one(db['File'], id=df['file_id'])
            p = db_folder + '/' + f['folder'] + '/' + f['filename']
            d_read = pydicom.read_file(p)
            instance = d_read[0x0020, 0x000d].value
            try:
                frame = d_read[0x0020, 0x0052].value
            except:
                # print(f'Cannot read the Frame of Reference UID of the Dicom {d.id}')
                continue
            if frame == frame_uid:
                if d['modality'] == 'CT':
                    im = syd.find_one(db['Image'], dicom_series_id=d['id'])
                    if im is not None:
                        res.append([d['id'], im['id']])
                    else:
                        res.append([d['id'], 0])
    if res != []:
        for r in res:
            print(f'The CT matching the input is in the DicomSeries Table with the id : {r[0]}')
            if r[1] != 0:
                print(f'The CT image is in the database with the id : {r[1]}')
            else:
                print('Could not find matching Image in the database')
    else:
        print("Cannot find matching CT")


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    nm2ct()
