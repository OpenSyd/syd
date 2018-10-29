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


FIXME UPDATE 





