
#!/usr/bin/env python3

import itk
import numpy as np

# -----------------------------------------------------------------------------
def itk_geometrical_mean(itk_image, k):

    # check 4 slices ANT POST etc
    z = itk_image.GetLargestPossibleRegion().GetSize()[2]
    if z != 4:
        s = 'Error, the image must have 4 slices'
        raise_except(s)

    # as np array (warning z is first now)
    array = itk.GetArrayViewFromImage(itk_image)
    ant_em = array[0,:,:]
    post_em = array[1,:,:]
    ant_sc = array[2,:,:]
    post_sc = array[3,:,:]

    # remove scatter
    ant = ant_em - k*ant_sc
    post = post_em - k*post_sc

    # clip negative values
    ant = np.clip(ant, 0, None)
    post = np.clip(post, 0, None)

    # flip post (?)

    # compute GM
    gm = np.sqrt(ant*post)

    # get np as itk image
    output = itk.GetImageFromArray(gm)

    # output.CopyInformation(itk_image) --> nope because 2D and 3D
    output.GetSpacing()[0] = itk_image.GetSpacing()[0]
    output.GetSpacing()[1] = itk_image.GetSpacing()[1]
    output.GetOrigin()[0] = itk_image.GetOrigin()[0]
    output.GetOrigin()[1] = itk_image.GetOrigin()[1]

    # FIXME
    # this is needed otherwise: bug in IndexToPointMatrix and
    # PointToIndexMatrix that are not computed ??
    itk.imwrite(output, "gm.mhd")
    output = itk.imread("gm.mhd")

    return output


