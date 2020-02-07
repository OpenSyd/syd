FIXME 

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

#Test

To run unit tests

```
python -m unittest syd_test -v
```

