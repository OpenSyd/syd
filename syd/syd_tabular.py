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

    table_name = syd.guess_table_name(db, table_name)
    formats = syd.find(db['PrintFormat'], table_name=table_name)
    df = None
    for f in formats:
        if f.name == format_name:
            df = f.format

    if df == None and format_name != 'raw':
        s = "Cannot find the format '"+format_name+"' in table '"+table_name+"' using 'raw'"
        syd.warning(s)
        format_name = 'raw'

    if format_name == 'raw':
        df = ''
        for k in element:
            df += '{'+str(k)+'} '

    return df

# -----------------------------------------------------------------------------
def get_nested_info(db, field_name):
    fields = field_name.split('.') #re.findall(r'(\w)\.(\w)', field_name)
    a = Box()
    a.table_names = []
    a.tables = []
    a.field_id_names = []
    a.field_format_name = ''
    for f in fields[0:-1]:
        tname = syd.guess_table_name(db, f)
        if tname in db:
            table = db[tname]
        else:
            table = None
        a.table_names.append(tname)
        a.tables.append(table)
        a.field_id_names.append(f+'_id')
        a.field_format_name += f+'->'

    a.field_format_name += fields[-1]
    a.field_name = fields[-1]
    a.initial_field_name = field_name
    return a


# -----------------------------------------------------------------------------
def get_sub_element(db, element, tables, field_id_names):
    se = element
    for table, field_id in zip(tables, field_id_names):
        if table:
            se = syd.find_join_one(se, table, field_id)
        else:
            return None
    return se


# -----------------------------------------------------------------------------
def get_sub_elements(db, elements, format_info, subelements):

    # format_info.field_format_name,      # study->patient->name
    # format_info.tables,                 # DicomStudy Patient
    # format_info.field_id_names,         # study_id patient_id
    # format_info.field_name)             # name

    # get al subelements
    current_table = format_info.tables[0]
    current_field_id_name = format_info.field_id_names[0]
    ids = [ elem[current_field_id_name] for elem in subelements] ## repetition, unique ? FIXME
    new_subelements = syd.find(current_table, id=ids)

    if len(format_info.tables) == 1:
        # correspondance current_id -> new_id
        subelements_map = {}
        for s in new_subelements:
            subelements_map[s.id] = s[format_info.field_name]
        for elem in elements:
            index = elem[format_info.field_format_name]
            if index: # because can be None
                elem[format_info.field_format_name] = subelements_map[index]
            else:
                elem[format_info.field_format_name] = '?'
        return elements

    # correspondance current_id -> new_id
    subelements_map = {}
    for s in new_subelements:
        subelements_map[s.id] = s[format_info.field_id_names[1]]

    # change the id
    for elem in elements:
        index = elem[format_info.field_format_name]
        if index:
            elem[format_info.field_format_name] = subelements_map[index]

    # recurse removing the first
    format_info.tables = format_info.tables[1:]
    format_info.field_id_names = format_info.field_id_names[1:]
    return get_sub_elements(db, elements, format_info, new_subelements)


# -----------------------------------------------------------------------------
def get_all_nested_info(db, line_format):
    subelements = re.findall(r'{(\w+)\.(.*?)[:\}]', line_format)
    nesteds = []
    for e in subelements:
        a = get_nested_info(db, e[0]+'.'+e[1])
        nesteds.append(a)
    return nesteds

# -----------------------------------------------------------------------------
def tabular_add_nested_elements(db, table_name, elements, line_format):

    # get information about all nesteds (such as patient->name
    fields_info = syd.get_all_nested_info(db, line_format)

    for sub in fields_info:
        for elem in elements:
            elem[sub.field_format_name] = elem[sub.field_id_names[0]] ## FIRST TIME ONLY
        se = get_sub_elements(db, elements, sub, elements)

    for sub in fields_info:
        line_format = line_format.replace(sub.initial_field_name, sub.field_format_name)

    return line_format


# -----------------------------------------------------------------------------
def tabular_add_special_fct(db, table_name, elements, line_format):

    subelements = re.findall(r'{(.*?)[:\}]', line_format)

    for sub in subelements:
        if sub == 'abs_filename':
            tabular_add_abs_filename(db, table_name, elements)
        if sub == 'time_from_inj':
            tabular_add_time_from_inj(db, table_name, elements)


# -----------------------------------------------------------------------------
def tabular_add_abs_filename(db, table_name, elements):

    # only for image, dicomstudy, dicomseries, dicomfile
    # image  -> file_mhd_id file_raw_id => file
    # study  -> NO
    # series -> => dicomfile => file_id ; several so only first one or all ?

    if table_name == 'DicomSeries':
        ids = [ e.id for e in elements]
        dicomfiles = syd.find(db['DicomFile'], dicom_series_id=ids)

        ids = [ df.file_id for df in dicomfiles ]
        files = syd.find(db['File'], id=ids)

        map_df = {df.dicom_series_id:df for df in dicomfiles} # keep only one
        map_f = {f.id:f for f in files} # keep only one

        for e in elements:
            df = map_df[e.id]
            f = map_f[df.id]
            e['abs_filename'] = syd.get_file_absolute_filename(db, f)

    if table_name == 'Image':
        ids = [ e.file_mhd_id for e in elements]
        files = syd.find(db['File'], id=ids)
        map_f = {f.id:f for f in files}

        for e in elements:
            f = map_f[e.file_mhd_id]
            e['abs_filename'] = syd.get_file_absolute_filename(db, f)


# -----------------------------------------------------------------------------
def tabular_add_time_from_inj (db, table_name, elements):

    if table_name != 'DicomSeries' and table_name != 'Image':
        return

    ids = [ e.injection_id for e in elements ]
    injections = syd.find(db['Injection'], id=ids)
    map_inj = {inj.id:inj for inj in injections} # keep only one    
    for e in elements:
        if not e.injection_id in map_inj:
            continue
        inj = map_inj[e.injection_id]
        date1 = inj.date
        date2 = e.acquisition_date
        #print(date1, date2)
        e.time_from_inj = date2-date1


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
        s += str_format_map(format_line, e)+'\n'

    # remove last element (final break line)
    s = s[:-1]
    return s

# -----------------------------------------------------------------------------
def grep_elements(elements, format_line, grep):
    '''
    Filter elements. Only keep the ones that match grep
    '''

    lines =  [ syd.str_format_map(format_line, elem) for elem in elements]

    s = ''
    if len(grep) == 0:
        for l in lines:
            s += l+'\n'
        if len(s)>0:
            s = s[:-1] # remove last break line
        return elements, s

    for g in grep:
        vgrep = False
        kelements = []
        klines = []
        if g[0] == '%':
            vgrep = True
            g = g[1:]
        for e,l in zip(elements, lines):
            if re.search(g, l):
                if not vgrep:
                    kelements.append(e)
                    klines.append(l)
            else:
                if vgrep:
                    kelements.append(e)
                    klines.append(l)
        elements = kelements
        lines = klines

    for l in lines:
        s += l+'\n'
    if len(s)>0:
        s = s[:-1] # remove last break line

    return elements, s
