#!/usr/bin/env python3

import dataset
from .syd_db import *

# -----------------------------------------------------------------------------
def add_tags(element, tags):
    if len(tags) == 0:
        return
    for tag in tags:
        add_tag(element, tag)


# -----------------------------------------------------------------------------
def add_tag(element, tag):
    if tag == None or tag =='':
        return

    # replace space by something else
    tag = tag.replace(' ', '_')

    # add tag
    if 'tags' in element:
        element['tags'] = element['tags']+" "+tag
    else:
        element['tags'] = tag
