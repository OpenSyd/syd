[![Documentation Status](https://readthedocs.org/projects/syd/badge/?version=latest)](https://syd.readthedocs.io/en/latest/?badge=latest)

SYD is a command-line environment and a python toolkit to perform image processing tasks on a database of medical images. It is initially developed to manage SPECT/CT images and perform tasks such as computing activity or integrated activity in various ROIs, in the field of Target Radionuclide Therapy and nuclear medicine.


use  ```git clone --recursive ``` or ```git submodule update --init```

SYD PY

# Main API

Create a new empty DB.

```
db = syd.create_db('mydatabase.db')
```

Open a db.

```
db = syd.open_db('mydatabase.db')
```

Insert elements in a table. The ```patient``` variable is a dict.

```
syd.insert(db['Patient'], patients)
syd.insert_one(db['Patient'], patient)
```

Delete elements in a table. The input is id or an array of ids.

```
syd.delete(db['Patient'], ids)
syd.delete_one(db['Patient'], id)
```

Update element in a table, the input is a dict, with 'id' key. 

```
syd.update_one(db['Patient'], patient)
```

Find elements. From ```syd.find```, element is a ```Box``` (a kind of
dictionnary that allow dot notation to retrieve the field value, ```elem.name```
instead of ```elem['name']```).

```
element = syd.find_one(db['Patient'], id=12)
elements = syd.find(db['Patient'], id=[12,14])
elements = syd.find(db['Patient'], name=['toto', 'titi'])

for e in elements:
     print(e.name)
```

# Dicom API

Search for all dicom series in the folder and add it to the db. Dicom are associated with patient_id (guess if == 0). 

```
syd.insert_dicom(db, folder, patient_id)
```

Helper to get all files associated with a dicom serie.

```
syd.get_dicom_serie_files(db, dicom_serie)
```

# Image API

Convert dicom series into image. 

```
syd.insert_image_from_dicom(db, dicom_serie)
```

Examples of helpers functions.

```
patient = syd.get_image_patient(db, image)
filename = syd.get_image_filename(db, image)
itk_image = syd.read_itk_image(db, image)
new_image = syd.insert_new_image(db, image, itk_image)
new_image = syd.insert_write_new_image(db, image, itk_image, tags)
```

# Test

To run unit tests

```
python -m unittest syd_test -v
```

# DataBase Structure

The SYD database is structured as follow :
- A Patient table containing the patient information and various id
- An Injection table, related to the patient table and containing all information about the injection of a radioisotope. This table uses the Radionuclide table that contains radionuclide properties and which is already pre-filled.
- An Acquisition table related to an injection, corresponding to the acquisition of some data with an imaging system. Dicom images and listmode data will refer to an acquisition. This table makes possible chronological display of all acquisitions related to an injection.
- A Listmode table containing the listmode data and associated files (see the table File below).
- A DicomStudy table containing all the Dicom studies for one patient
- A DicomSerie table containing series for one study and linked to one Acquisition. An Acquisition is linked to all the associated DicomSeries and listmode data.
- A DicomFile table containing details about the dicom file.
- An Image table that groups all images that will be created. Usually stored as .mhd/.raw files.
- A File table that store path for all the files included in the database

# View

In ```syd_find```, the resulting table of elements is printed with a panda dataframe. The elements are extracted from
 the database via either the raw elements in the table or via a view. The views are defined in the FormatView table
  and created with ```syd_clear_view --default``` or database creations. Additional view can be created with the
   ```syd_insert_view``` command.  

