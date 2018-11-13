FIXME 

SYD PY

# Main API

Create a new empty DB.

```
db = syd.create_db('mydatabase'.db')
```

Open a db.

```
db = syd.open_db('mydatabase.db')
```

Insert elements in a table. The info is a dict.

```
syd.insert(db['Patient'], patients_info)
syd.insert_one(db['Patient'], patient_info)
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

Helpers to get linked elements.

```
patient = syd.get_image_patient(db, image)
filename = syd.get_image_filename(db, image)
```

FIXME
syd.insert_image(db, filename, patient_id)
syd.update_image(image, dicom_serie)
what about img size spacing etc ? keep in db ? 

