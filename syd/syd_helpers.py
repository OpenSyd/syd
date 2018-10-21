#!/usr/bin/env python3

from datetime import datetime

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
