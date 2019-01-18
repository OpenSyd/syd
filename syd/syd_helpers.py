#!/usr/bin/env python3

import datetime
import colored
import os
from tokenize import tokenize, NUMBER
from io import BytesIO

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
def print_elements(table_name, print_format, elements):
    '''
    Pretty print some elements
    FIXME use table_name + print_format to pretty print
    FIXME rename to pretty_print
    '''

    for e in elements:
        s = ' '.join(str(x) for x in e.values())
        print(s)


# -----------------------------------------------------------------------------
def print_elements(elements):
    '''
    Pretty print some elements
    FIXME use table_name + print_format to pretty print
    '''

    for e in elements:
        s = ' '.join(str(x) for x in e.values())
        print(s)


# -----------------------------------------------------------------------------
def printe(element):
    s = ''
    for v in element.values():
        s += str(v)+' '
    print(s)

