#!/usr/bin/env python3

import itk
import numpy as np

# -----------------------------------------------------------------------------
def itk_geometrical_mean(image, k):

    # check 4 slices ANT POST etc
    z = image.GetLargestPossibleRegion().GetSize()[2]
    if z != 4:
        s = 'Error, the image must have 4 slices'
        raise_except(s)

    # as np array (warning z is first now)
    array = itk.GetArrayViewFromImage(image)

    ant_em = array[0,:,:]
    post_em = array[1,:,:]
    ant_sc = array[2,:,:]
    post_sc = array[3,:,:]

    # remove scatter
    ant = ant_em - k*ant_sc
    post = post_em - k*post_sc

    # flip post (?)

    # compute GM
    gm = np.sqrt(ant*post)

    # create the output 2D itk image
    output = itk.GetImageFromArray(gm)
    output.GetSpacing()[0] = image.GetSpacing()[0]
    output.GetSpacing()[1] = image.GetSpacing()[1]
    output.GetOrigin()[0] = image.GetOrigin()[0]
    output.GetOrigin()[1] = image.GetOrigin()[1]

    return output


