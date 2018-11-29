#!/usr/bin/env python3

import itk
import numpy as np

# -----------------------------------------------------------------------------
def itk_crop_planar(image, ymax):
    '''
    Crop pixels larger than ymax (in pixel), sup-inf dimension
    '''

    # get size and change y
    size = image.GetLargestPossibleRegion().GetSize()
    size[1] = ymax
    region = image.GetLargestPossibleRegion();
    region.SetSize(size)

    # declare crop filter
    ImageType = type(image)
    f = itk.RegionOfInterestImageFilter[ImageType,ImageType].New()
    f.SetRegionOfInterest(region)
    f.SetInput(image)

    # go
    f.Update()
    return f.GetOutput()


