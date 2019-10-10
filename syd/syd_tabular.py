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
def get_subfield_info(db, field_name):
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
def get_all_subfield_info(db, line_format):
    subelements = re.findall(r'{(\w+)\.(.*?)[:\}]', line_format)
    subfields = []
    for e in subelements:
        a = get_subfield_info(db, e[0]+'.'+e[1])
        subfields.append(a)
    return subfields

# -----------------------------------------------------------------------------
def add_subfields_to_elements(db, tables_name, elements, line_format):

    # get information about all subfields (such as patient->name
    fields_info = syd.get_all_subfield_info(db, line_format)

    for sub in fields_info:
        for elem in elements:
            elem[sub.field_format_name] = elem[sub.field_id_names[0]] ## FIRST TIME ONLY
        se = get_sub_elements(db, elements, sub, elements)

    for sub in fields_info:
        line_format = line_format.replace(sub.initial_field_name, sub.field_format_name)

    return line_format


# -----------------------------------------------------------------------------
def add_subfields_to_elements_old(db, elements, fields_info):

    for elem in elements:
        for sub in fields_info:
        ## --> FIXME THIS IS VERY SLOW
            se = get_sub_element(db, elem, sub.tables, sub.field_id_names)
            if se and sub.field_name in se:
                elem[sub.field_format_name] = se[sub.field_name]

    return elements


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
