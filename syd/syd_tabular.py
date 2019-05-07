#!/usr/bin/env python3

import datetime
import colored
import os
import syd
import re
from tokenize import tokenize, NUMBER
from io import BytesIO
from box import Box, BoxKeyError

# -----------------------------------------------------------------------------
def tabular_get_line_format(db, table_name, format_name, element):
    '''
    Retrieve the line format from the format name to build a tabluar
    '''

    formats = syd.find(db['PrintFormat'], table_name=table_name)
    df = None
    for f in formats:
        if f.name == format_name:
            df = f.format

    if df == None:
        s = "Cannot find the format '"+format_name+"' in table '"+table_name+"' using 'raw'"
        syd.warning(s)
        format_name = 'raw'

    if format_name == 'raw':
        df = ''
        for k in element:
            df += '{'+str(k)+'} '
        df += '\n'

    return df

# -----------------------------------------------------------------------------
def tabular(db, table_name, line_format, elements):
    '''
    Pretty dump some elements with a tabular
    Modify the elements to include sub-fields
    '''
    
    # find all sub-fields XXX.YYY and add the corresponding fields in the elements list
    f = line_format

    # with three levels
    subelements = re.findall(r'{\w+\.\w+\.\w+', f)
    tables1 = []
    tables2 = []
    fields = []
    for e in subelements:
        spl = e.split('.')
        table1 = spl[0][1:] # remove first '{'
        table2 = spl[1] # remove first '{'
        field = spl[2]
        tables1.append(table1)
        tables2.append(table2)
        fields.append(field)
        f = f.replace(table1+'.'+table2+'.'+field, table1+'_'+table2+'_'+field, 1)

    # add fields in elements
    for e in elements:
        for table1, table2, field in zip(tables1, tables2, fields):
            # consider table.field -> Table and add field to the current element
            eid1 = table1+'_id'
            eid1 = e[eid1]
            subelem = syd.find_one(db[table1.capitalize()], id=eid1)
            subelem = syd.find_one(db[table2.capitalize()], id=subelem[table2+'_id'])
            e[table1+"_"+table2+"_"+field] = subelem[field]
                
    # with two levels
    subelements = re.findall(r'{\w+\.\w+', f)
    tables = []
    fields = []
    for e in subelements:
        spl = e.split('.')
        table = spl[0][1:] # remove first '{'
        field = spl[1]
        tables.append(table)
        fields.append(field)
        f = f.replace(table+'.'+field, table+'_'+field, 1)

    # add fields in elements
    for e in elements:
        for table, field in zip(tables, fields):
            # consider table.field -> Table and add field to the current element
            eid = table+'_id'
            eid = e[eid]
            subelem = syd.find_one(db[table.capitalize()], id=eid)
            e[table+"_"+field] = subelem[field]
                
    subelements = re.findall(r'{absolute_filename', f)

    for s in subelements:
        if (table_name == 'DicomSerie'):
            for e in elements:
                files = syd.get_dicom_serie_files(db, e)
                e['absolute_filename'] = syd.get_file_absolute_filename(db, files[0])
        if (table_name == 'Image'):
            for e in elements:
                fn = syd.get_image_filename(db, e)
                e['absolute_filename'] = fn
        if (table_name == 'File'):
            for e in elements:
                fn = syd.get_file_absolute_filename(db, e)
                e['absolute_filename'] = fn
        if (table_name == 'DicomFile'):
            for e in elements:
                fi = syd.find_one(db['File'], id=e.file_id)
                fn = syd.get_file_absolute_filename(db, fi)
                e['absolute_filename'] = fn

    # add header
    lfh = f
    subelements = re.findall(r'{\w+', lfh)
    header = ''
    e = {}
    for s in subelements:
        s = s[1:]
        e[s] = s
        header += s+' '
    #print('before', lfh)
    #lfh = re.sub(r':([0-9.]*)d',r':\1', lfh)
    #lfh = re.sub(r':([0-9.]*)f',r':\1', lfh)
    #print('after', lfh)
    #print(lfh)
    #print('e', e)
    #print(lfh.format_map(e))
    print(header)
                
    return tabular_str(f, elements);

# -----------------------------------------------------------------------------
def tabular_str(format_line, elements):
    '''
    Dump some elements with a tabular
    '''

    # check
    try:
        t = format_line.format_map(elements[0])
    except BoxKeyError as err:
        s = "Error while formating "+str(err)+" probably does not exist in this table"
        raise_except(s)

    s = ''
    for e in elements:
        s += format_line.format_map(e)

    # remove last element (final break line)
    s = s[:-1]
    return s
