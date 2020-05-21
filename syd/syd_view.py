#!/usr/bin/env python3

from box import Box, BoxList
from sqlalchemy import exc

import syd


# -----------------------------------------------------------------------------
def create_format_view_table(db):
    """
    Create the injection table
    """

    # create Injection table
    q = 'CREATE TABLE FormatView (\
    id INTEGER PRIMARY KEY NOT NULL,\
    view_name TEXT NOT NULL UNIQUE,\
    table_name TEXT NOT NULL,\
    format TEXT\
    )'
    db.query(q)


# -----------------------------------------------------------------------------
def get_view_names(db):
    s = f"SELECT name from sqlite_master WHERE type ='view';"
    res = db.query(s)
    views = []
    for v in res:
        views.append(v['name'])
    return views


# -----------------------------------------------------------------------------
def parse_columns_view_format(db, view_format):
    the_format = {}
    columns_format = view_format.split(' ')

    for c in columns_format:
        # get the format, always at the end separated with ':' (optional)
        cc = c.split(':')
        col_left = cc[0].lstrip().rstrip()
        if col_left == '':
            continue
        if len(cc) > 1:
            col_format = ':' + cc[1]
        else:
            col_format = ''

        # get the column name
        cc = col_left.split('=')
        col_left = cc[0]
        col_name = col_left
        if len(cc) > 1:
            col_name = cc[1]

        # get the nested tables and the id
        nested_tables = col_left.split('.')
        col_id = nested_tables[-1]
        col_tables = nested_tables[0:-1]

        # FIXME check if a table is NONE
        for t in col_tables:
            tt = syd.guess_table_name(db, t)
            if not tt:
                print(f'Error table {t} is not known')
                exit(0)

        # get the real table names
        col_tables = [syd.guess_table_name(db, t) for t in col_tables]

        # check that nested element exist
        if len(col_tables) > 0:
            if col_id not in db[col_tables[-1]].columns:
                print(f'Error, column {col_id} not in table {col_tables[-1]}')
                exit(0)

        # check duplicated col name
        if col_name in the_format:
            # FIXME raise execption ?
            print(f'error, {col_name} already exist ')
            exit(0)
        the_format[col_name] = {'id': col_id, 'format': col_format, 'tables': col_tables}
    return Box(the_format)


# -----------------------------------------------------------------------------
def create_view_query_from_format(name, table, columns_format):
    """
    Build a SQL query to create a view.
    """
    s = f'CREATE VIEW {name} AS SELECT \n'

    for col in columns_format:
        c = columns_format[col]
        # replace . by '_' in the col name
        acol = col.replace('.', '_')
        # explicit the table even for the current one
        if len(c['tables']) == 0:
            c['id'] = f"{table}.{c['id']}"
            a = c['id'] + ' as ' + acol + ', \n'
        else:
            # use the last one in the list of nested tables
            a = c['tables'][-1] + '.' + c['id'] + ' as ' + acol + ', \n'
        # remove last comma
        s += a

    # remove last not useful  characters
    s = s[:-3] + ' \n'
    s += f'FROM {table}\n'

    # inner join
    already_done = []
    for col in columns_format:
        c = columns_format[col]
        tables = c['tables']
        if len(tables) == 0:
            continue
        nt = len(tables)
        for i in range(nt):
            t1 = tables[i]
            if i == 0:
                t2 = table
            else:
                t2 = tables[i - 1]
            if t1 != '' and t1 not in already_done:
                # the foreign key is tablename_id except for 'Dicom_XXX'
                tt = t1.lower()
                if 'dicom' in tt:
                    tt = 'dicom_'+tt[5:]
                s += f'INNER JOIN {t1} ON {t1}.id = {t2}.{tt}_id '
                s += '\n'
                already_done.append(t1)
    return s


def insert_view(db, name, table, view_format):
    """
    Create a SQL view and a description in the table FormatView (used for printing)
    """

    # get the list of columns
    table = syd.guess_table_name(db, table)
    columns_format = syd.parse_columns_view_format(db, view_format)

    # check column id
    # needed because sqlite do not consider up/low case while Box yes
    for col in columns_format:
        c = columns_format[col]
        if len(c.tables) == 0:
            t = table
        else:
            t = c.tables[-1]
        if c.id not in db[t].columns:
            # special case: add column labels if does not exist
            if c.id == 'labels':
                print("(Add a 'labels' column)")
                db[t].create_column('labels', db.types.text)
        if c.id not in db[t].columns:
            s = f"Error, cannot find the column '{c.id}' in the table {t}\n"
            s += f'Columns are {db[t].columns}'
            syd.raise_except(s)


    # TODO check if view already exist ?
    name = table + '_' + name
    s = f'DROP VIEW IF EXISTS {name} ;'
    db.query(s)

    # create sql query to create the view
    s = syd.create_view_query_from_format(name, table, columns_format)

    # create the view
    db.query(s)

    # test the view
    ts = f"SELECT * from {name}"
    txt = ''
    try:
        db.query(ts)
        n = db[name].count()
        txt = f'View {name} has been created with {n} elements'
    except exc.OperationalError as e:
        a = f'Error : view error with {ts}\n'
        a += f'The initial query was \n{s}\n'
        a += str(e)
        syd.raise_except(a)

    # create/update element in the table FormatView
    view = syd.find_one(db['FormatView'], view_name=name)
    updated = True
    if not view:
        updated = False
        view = Box()
    view.view_name = name
    view.table_name = table
    view.format = view_format
    if updated:
        syd.update_one(db['FormatView'], view)
    else:
        syd.insert_one(db['FormatView'], view)

    return txt


def insert_default_views(db):
    dd = [
        {   'name': 'default',
            'table': 'Patient',
            'format': 'id:3 num:3 name:<20 dicom_id:<10 labels sex '},

        {   'name': 'default',
            'table': 'Radionuclide',
            'format': 'id:3 name:<10 element:<12 atomic_number=Z:4d \
            mass_number=A:4d metastable=m:2 half_life_in_hours:8.2f \
            max_beta_minus_energy_in_kev=Q:8.2f labels'},

        {   'name': 'default',
            'table': 'Injection',
            'format': 'id:4 patient.name=P:<5 \
            radionuclide.name=rad:5 activity_in_mbq=MBq:8.2f  \
            date cycle labels'},

        {   'name': 'default',
            'table': 'DicomStudy',
            'format': 'id:4 patient.name=P:<5 \
            study_description=dec study_name=S_name labels'},

        {   'name': 'default',
            'table': 'DicomSeries',
            'format': 'id acquisition_id=acq_id \
            dicom_study.patient.name=P:<10 injection.radionuclide.name=rad \
            injection.activity_in_mbq=MBq:8.2f \
            injection.cycle=cycle \
            modality content_type acquisition_date=acq_date \
            image_size image_spacing \
            series_description \
            dicom_study.study_description=study_desc \
            dicom_study.study_name=sname dataset_name labels'},

        {
            'name': 'default',
            'table': 'Image',
            'format': 'id patient.name=P:<5\
            modality acquisition_date=acq_date\
            injection.radionuclide.name=rad:5 \
            injection.date=inj_date \
            dicom_series_id=series\
            dicom_series.acquisition_id=acq_id\
            pixel_type pixel_unit \
            dicom_series.series_description=desc \
            dicom_series.dicom_study.study_description=study_desc \
            dicom_series.dataset_name=dataset labels'},

    ]
    dd = BoxList(dd)
    for d in dd:
        txt = insert_view(db, d.name, d.table, d.format)
        print(txt)


