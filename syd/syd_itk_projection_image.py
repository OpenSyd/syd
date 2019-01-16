#!/usr/bin/env python3

import itk
import SimpleITK as sitk
import numpy as np

# -----------------------------------------------------------------------------
def itk_projection_image(itk_image, axe=1):

    # get image type
    ImageType = type(itk_image)
    OutputImageType = itk.Image[itk.F,2]

    # projection filter
    f = itk.SumProjectionImageFilter[ImageType, OutputImageType].New()
    f.SetProjectionDimension(axe)
    f.SetInput(itk_image)
    f.Update()
    output = f.GetOutput()

    return output


