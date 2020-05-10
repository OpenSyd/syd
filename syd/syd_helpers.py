#!/usr/bin/env python3

import datetime
import colored
import os
import syd
import re
from tokenize import tokenize, NUMBER
from io import BytesIO
from box import Box, BoxKeyError
from difflib import SequenceMatcher

# -----------------------------------------------------------------------------
def replace_key_with_id(element, key_name, table, table_key_name):
    '''
    Replace the key 'key_name' in the element (dict) with the id of the
    element find in the table
    '''
    #p = table.find_one(table_key_name=element[key_name])
    statement = 'SELECT id FROM '+table.name+' WHERE '+table_key_name+' = "'+element[key_name]+'"'
    i = 0
    s = element[key_name]
    res = table.db.query(statement)
    for row in res:
        if (i != 0):
            s = 'Error, table {} has several elements with {}={}'.format(table.name, table_key_name, s)
            raise_except(s)
        element.pop(key_name)
        k = table.name.lower()+'_id'
        element[k] = row['id']
        i = i +1
    if (i ==0):
        s = 'Error, table {} does not contain element with {}={}'.format(table.name, table_key_name, s)
        raise_except(s)

    return element


# -----------------------------------------------------------------------------
def str_to_date(str):
    '''
    Convert string to datetime
    '''

    # FIXME -> deal with error
    try:
        date = datetime.datetime.strptime(str, '%Y-%m-%d %H:%M:%S')
        return date
    except:
        pass

    try:
        date = datetime.datetime.strptime(str, '%Y-%m-%d %H:%M')
        return date
    except:
        pass
    s = f'Error, cannot convert {str} to a Y-m-d H:M[:S] date '
    syd.raise_except(s)
    return date


# -----------------------------------------------------------------------------
def dcm_str_to_date(str):
    '''
    Convert dicom string to datetime
    '''

    # remove remaining characters
    st = str[0:15]

    # FIXME -> deal with error
    try:
        date = datetime.datetime.strptime(st, '%Y%m%d %H%M%S')
    except:
        print('Error converting date', st, str)
    return date

# -----------------------------------------------------------------------------
# color constant
color_error = colored.fg("red") + colored.attr("bold")
color_warning = colored.fg("orange_1")

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
def str_match(a, b):
    '''
    Distance between strings
    '''
    return SequenceMatcher(None, a, b).ratio()

# -----------------------------------------------------------------------------
def guess_table_name(db, table_name):
    '''
    Guess table name according to closest str distance.
    Return None if the match is lower than 0.5
    '''
    if table_name in db:
        return table_name

    max_match = 0
    f = ''
    for t in db.tables:
        d = syd.str_match(table_name, str(t))
        if d > max_match:
            f = str(t)
            max_match = d

    if max_match < 0.5:
        return None
    return f

# -----------------------------------------------------------------------------
def filter_elements(elements, grep):
    '''
    Return the list of elements that match the grep
    '''
    if len(grep) == 0:
        return elements

    res = []
    for e in elements:
        # make a str
        s = ''.join(str(x) for x in e.values())
        found=True
        for g in grep:
            if not re.search(g, s):
                found=False
                break
            if found:
                res.append(e)

    return res


# -----------------------------------------------------------------------------
def update_nested(db, elements):
    '''
    Update all nested elements (see update_nested_one)
    '''
    for e in elements:
        update_nested_one(db, e)
    
   
# -----------------------------------------------------------------------------
def update_nested_one(db, element):
    '''
    Consider an input element having nested element. Update them.

    For example, if patient is {id:'1', injection:{id:12, ...}, injection_id:12, ...}
    the nested injection will be updated
    '''

    m = {}
    for k in element:
        if not k[-3:] == '_id':
            continue

        field = k[:-3]
        table = syd.guess_table_name(db, field)
        if table == None: # may append for xample with dicom_id
            continue
        eid = element[k]
        nested_elem = syd.find_one(db[table], id=eid)
        if nested_elem == None:
            continue
        m[field] = nested_elem

    for f in m:
        update_nested_one(db, m[f])
        element[f] = m[f]



