#!/usr/bin/env python3

import datetime
import colored
import os
import syd
import re
from tokenize import tokenize, NUMBER
from io import BytesIO
from box import Box, BoxKeyError

from functools import reduce
from operator import attrgetter
from string import Formatter

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
    # If not found -> ignore the field
    for e in elements:
        for table1, table2, field in zip(tables1, tables2, fields):
            # consider table.field -> Table and add field to the current element
            eid1 = table1+'_id'
            eid1 = e[eid1]
            table1_name = table1.replace('_',' ').title().replace(' ','')
            table2_name = table2.replace('_',' ').title().replace(' ','')
            subelem = syd.find_one(db[table1_name], id=eid1)
            if subelem != None:
                subelem = syd.find_one(db[table2_name], id=subelem[table2+'_id'])
                if subelem != None:
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
    # If not found -> ignore the field
    for e in elements:
        for table, field in zip(tables, fields):
            # consider table.field -> Table and add field to the current element
            eid = table+'_id'
            eid = e[eid]
            table_name = table.replace('_',' ').title().replace(' ','')
            subelem = syd.find_one(db[table_name], id=eid)
            if subelem != None:
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
def get_field_value(field_name, mapping):
    '''
    http://ashwch.github.io/handling-missing-keys-in-str-format-map.html
    To handle missing field in tabular_str
    '''
    try:
        if '.' not in field_name:
            return mapping[field_name], True
        else:
            obj, attrs = field_name.split('.', 1)
            return attrgetter(attrs)(mapping[obj]), True
    except Exception as e:
        return field_name, False


# -----------------------------------------------------------------------------
def str_format_map(format_string, mapping):
    '''
    http://ashwch.github.io/handling-missing-keys-in-str-format-map.html
    To handle missing field in tabular_str
    '''
    f = Formatter()
    parsed = f.parse(format_string)
    output = []
    for literal_text, field_name, format_spec, conversion in parsed:
        conversion = '!' + conversion if conversion is not None else ''
        format_spec = ':' + format_spec if format_spec else ''
        if field_name is not None:
            field_value, found = get_field_value(field_name, mapping)
            if not found:
                # text = '{{{}{}{}}}'.format(field_value,
                #                            conversion,
                #                            format_spec)
                text = '?'
            else:
                format_string = '{{{}{}}}'.format(conversion, format_spec)
                text = format_string.format(field_value)
        output.append(literal_text + text)
        text = ''
    return ''.join(output)

# -----------------------------------------------------------------------------
def tabular_str(format_line, elements):
    '''
    Dump some elements with a tabular
    '''

    # check
    try:
        #t = format_line.format_map(SafeKey(d))
        t = str_format_map(format_line, elements[0])
        
    except BoxKeyError as err:
        s = "Error while formating "+str(err)+" probably does not exist in this table"
        raise_except(s)

    s = ''
    for e in elements:
        #s += format_line.format_map(d)
        s += str_format_map(format_line, e)

    # remove last element (final break line)
    s = s[:-1]
    return s
