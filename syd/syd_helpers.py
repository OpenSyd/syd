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
def str_to_date(str):
    '''
    Convert string to datetime
    '''

    # FIXME -> deal with error
    date = datetime.datetime.strptime(str, '%Y-%m-%d %H:%M')
    return date


# -----------------------------------------------------------------------------
def dcm_str_to_date(str):
    '''
    Convert dicom string to datetime
    '''

    # remove remaining characters
    str = str[0:15]

    # FIXME -> deal with error
    date = datetime.datetime.strptime(str, '%Y%m%d %H%M%S')
    return date


# -----------------------------------------------------------------------------
# color constant
color_error = colored.fg("red") + colored.attr("bold")
color_warning = colored.fg("orange_4a")

# -----------------------------------------------------------------------------
# color constant
def fatal(s):
    s = colored.stylize(s, color_error)
    print(s)
    exit(0)

# -----------------------------------------------------------------------------
# color constant
def warning(s):
    s = colored.stylize(s, color_warning)
    print(s)

# -----------------------------------------------------------------------------
# color constant
def raise_except(s):
    s = colored.stylize(s, color_error)
    raise Exception(s)

# -----------------------------------------------------------------------------
def build_folder(db, pname, date, modality):
    folder = os.path.join(pname, date)
    folder = os.path.join(folder, modality)
    return folder


# -----------------------------------------------------------------------------
def parse_piped_input(l):
    # if input is void, we parse piped input as a string
    # and extract all ids
    if not l:
        l = input()
        dd = tokenize(BytesIO(l.encode('utf-8')).readline)
        l = []
        for toknum, tokval, _, _, _ in dd:
            if toknum == NUMBER:
                l.append(tokval)
    return l


# -----------------------------------------------------------------------------
def dump_elements(elements):
    '''
    Pretty dump some elements
    FIXME use table_name + dump_format to pretty dump
    '''

    for e in elements:
        s = ' '.join(str(x) for x in e.values())
        print(s)


# -----------------------------------------------------------------------------
def dump(element):
    s = ''
    for v in element.values():
        s += str(v)+' '
    print(s)

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

    subelements = re.findall(r'{filename', f)

    for s in subelements:
        if (table_name == 'DicomSerie'):
            for e in elements:
                files = syd.get_dicom_serie_files(db, e)
                e['filename'] = syd.get_file_absolute_filename(db, files[0])
        if (table_name == 'Image'):
            for e in elements:
                fn = syd.get_image_filename(db, e)
                e['filename'] = fn
            
    return tabular_str(f, elements);

# -----------------------------------------------------------------------------
def tabular_str(format_line, elements):
    '''
    Pretty dump some elements with a tabular
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
