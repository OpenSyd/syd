#!/usr/bin/env python3

import dataset
import collections
from .syd_db import *


# -----------------------------------------------------------------------------
def add_labels(elements, labels):
    '''
    Main fct to add some labels to some elements.

    - If element is not an array, build an array.
    - If labels is a str, split it in array
    
    '''

    # check if elements is a list
    if not isinstance(elements, collections.Sequence):
            return add_labels([elements], labels)

    # convert labels into array if it is not
    if type(labels) == type('str'):
        labels = labels.split(' ')

    if len(labels) == 0:
        return

    all_labels = ''
    for t in labels:
        t = t.strip() # remove space
        all_labels = all_labels+' '+t

    for e in elements:
        if 'labels' in e and e.labels != None :
            e.labels = e.labels+" "+all_labels
        else:
            e.labels = t

    # remove duplicate
    for e in elements:
        l = set(e.labels.split(' '))
        e.labels = ' '.join(l)

# -----------------------------------------------------------------------------
def rm_labels(elements, labels):

    # check if elements is a list
    if not isinstance(elements, collections.Sequence):
            return rm_labels([elements], labels)

    # convert labels into array if it is not
    if type(labels) == type('str'):
        labels = labels.split(' ')

    if len(labels) == 0:
        return

    for t in labels:
        t = t.strip() # remove space
        for e in elements:
            if 'labels' in e:
                e.labels = e.labels.replace(t, '')
            else:
                e.labels = t

# -----------------------------------------------------------------------------
def clean_labels(elements):

    for e in elements:
        if 'labels' in e:
            e.labels = ''
