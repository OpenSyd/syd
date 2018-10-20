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
