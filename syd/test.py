#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dataset


db = dataset.connect('sqlite:///synfrizz.db')

# for t in db.tables:
#     print('Table',t)

patient_table = db['syd::Patient']

print(patient_table.columns)
print(len(patient_table))

patients = patient_table.all()

# for p in patients:
#     print(p)

#patients = patient_table.find(study_id=[5,3,8])
#patients = patient_table.find(study_id={'>': 3})
print('table', patient_table.table)
print('cols', patient_table.table.columns)
patients = patient_table.find(patient_table.table.columns.study_id >= 9)
for p in patients:
    print(p)

# update one given patient
p1 = patient_table.find_one(study_id=8)
print(p1)

file_table = db['syd::File']
print(len(file_table))

# for f in file_table.all():
#     print(f['filename'])

