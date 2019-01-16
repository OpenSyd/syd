#!/usr/bin/env python3

import itk
import SimpleITK as sitk
import numpy as np

# -----------------------------------------------------------------------------
def itk_register_planar_images(itk_planar1, itk_planar2):

    # check dimension
    if itk_planar1.GetImageDimension() != 2:
        s = 'itk_planar1 must be 2D, while type is '+type(itk_planar1)
        syd.raise_except(s)
    if itk_planar2.GetImageDimension() != 2:
        s = 'itk_planar2 must be 2D, while type is '+type(itk_planar2)
        syd.raise_except(s)

    # get info in np array
    size1 = np.array(itk_planar1.GetLargestPossibleRegion().GetSize())
    size2 = np.array(itk_planar2.GetLargestPossibleRegion().GetSize())
    spacing1 = np.array(itk_planar1.GetSpacing())
    spacing2 = np.array(itk_planar2.GetSpacing())
    origin1 = np.array(itk_planar1.GetOrigin())
    origin2 = np.array(itk_planar2.GetOrigin())

    # resample first image like the second
    ImageType = type(itk_planar1)
    f = itk.ResampleImageFilter[ImageType, ImageType].New()
    #interp = itk.BSplineInterpolateImageFunction[ImageType].New()
    #interp.SetSplineOrder(3)
    transform = itk.IdentityTransform[itk.D, 2].New()
    transform.SetIdentity()

    size3 = size1*spacing1/spacing2
    size3 = size3.astype(int).tolist()
    f.SetInput(itk_planar1)
    f.SetTransform(transform)
    #f.SetInterpolator(interp)
    f.SetOutputOrigin(itk_planar1.GetOrigin())
    f.SetOutputSpacing(itk_planar2.GetSpacing())
    f.SetSize(size3)
    f.Update()
    itk_planar1_resampled = f.GetOutput()

    # info
    spacing3 = itk_planar1_resampled.GetSpacing()
    origin3 = itk_planar1_resampled.GetOrigin()

    # MI filter
    f = itk.MattesMutualInformationImageToImageMetric[ImageType, ImageType].New()
    interp = itk.NearestNeighborInterpolateImageFunction[ImageType,itk.D].New()
    tmax = size3[1]+size2[1]
    regionM = itk_planar2.GetLargestPossibleRegion()
    regionF = itk_planar1_resampled.GetLargestPossibleRegion()
    region = regionF
    amin = 99999
    tmin = 0
    for t in range(tmax):
        origin = np.array(origin2)
        origin[1] = origin2[1] - t*spacing2[1]
        itk_planar2.SetOrigin(origin)

        f.SetMovingImage(itk_planar2)
        f.SetFixedImage(itk_planar1_resampled)

        transform = itk.IdentityTransform[itk.D, 2].New()
        transform.SetIdentity()
        f.SetTransform(transform)
        f.SetFixedImageRegion(region)
        f.SetFixedImageSamplesIntensityThreshold(2)
        f.SetUseFixedImageSamplesIntensityThreshold(True)

        f.SetInterpolator(interp)
        #f.UseAllPixelsOff()
        f.UseAllPixelsOn()
        #f.SetNumberOfSpatialSamples(500)
        f.SetNumberOfHistogramBins(50)
        f.ReinitializeSeed()
        f.Initialize()

        try:
            a = f.GetValue(transform.GetParameters())
        except:
            t = tmax+1
            a = 999999
            break
        if a<amin:
            amin = a
            tmin = t

    # end
    origin = np.array(origin2)
    origin[1] = origin2[1] - tmin*spacing2[1]
    itk_planar2.SetOrigin(origin)
    return itk_planar2, tmin

