#!/usr/bin/env python3

from datetime import datetime
import colored

# -----------------------------------------------------------------------------
def str_to_date(str):
    '''
    Convert string to datetime
    '''

    # FIXME -> deal with error
    date = datetime.strptime(str, '%Y-%m-%d %H:%M')
    return date


# -----------------------------------------------------------------------------
def dcm_str_to_date(str):
    '''
    Convert dicom string to datetime
    '''

    # remove remaining characters
    str = str[0:15]

    # FIXME -> deal with error
    date = datetime.strptime(str, '%Y%m%d %H%M%S')
    return date


# -----------------------------------------------------------------------------
# color constant
color_error = colored.fg("red") + colored.attr("bold")

# -----------------------------------------------------------------------------
# color constant
def fatal(s):
    s = colored.stylize(s, color_error)
    print(s)
    exit(0)

# -----------------------------------------------------------------------------
# color constant
def raise_except(s):
    s = colored.stylize(s, color_error)
    raise Exception(s)

