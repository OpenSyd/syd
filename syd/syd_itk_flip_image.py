#!/usr/bin/env python3

import itk
import numpy as np

# -----------------------------------------------------------------------------
def itk_flip_image(itk_image, axe=1):

    # get image type
    ImageType = type(itk_image)
    OutputImageType = itk.Image[itk.F,2]

    # projection filter
    # f = itk.SumProjectionImageFilter[ImageType, OutputImageType].New()
    # f.SetProjectionDimension(axe)
    f = itk.FlipImageFilter[ImageType].New()
    #typename FlipImageFilterType::FlipAxesArrayType axes;
    #axes.Fill(false);
    #axes[axe]=true;
    f.SetFlipAxes(1);
    f.SetFlipAboutOrigin(True);
    f.SetInput(itk_image)
    f.Update()
    output = f.GetOutput()

    return output


