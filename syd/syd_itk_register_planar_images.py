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
    print(type(itk_planar1))
    print(type(itk_planar2))

    # get info in np array
    size1 = np.array(itk_planar1.GetLargestPossibleRegion().GetSize())
    size2 = np.array(itk_planar2.GetLargestPossibleRegion().GetSize())
    spacing1 = np.array(itk_planar1.GetSpacing())
    spacing2 = np.array(itk_planar2.GetSpacing())
    origin1 = np.array(itk_planar1.GetOrigin())
    origin2 = np.array(itk_planar2.GetOrigin())
    print('sizes', size1, size2)
    print('spacing', spacing1, spacing2)
    print('origin', origin1, origin2)

    # resample first image like the second
    ImageType = type(itk_planar1)
    f = itk.ResampleImageFilter[ImageType, ImageType].New()
    #interp = itk.BSplineInterpolateImageFunction[ImageType].New()
    #interp.SetSplineOrder(3)
    transform = itk.IdentityTransform[itk.D, 2].New()
    transform.SetIdentity()

    size3 = size1*spacing1/spacing2
    size3 = size3.astype(int).tolist()
    print('size3', size3)

    f.SetInput(itk_planar1)
    f.SetTransform(transform)
    #f.SetInterpolator(interp)
    f.SetOutputOrigin(itk_planar1.GetOrigin())
    f.SetOutputSpacing(itk_planar2.GetSpacing())
    f.SetSize(size3)
    f.Update()
    itk_planar1_resampled = f.GetOutput()

    itk.imwrite(itk_planar1_resampled, 'resample.mhd') ## FIXME
    itk.imwrite(itk_planar2, 'planar2.mhd') ## FIXME
    itk.imwrite(itk_planar1, 'planar1.mhd') ## FIXME

    # info
    spacing3 = itk_planar1_resampled.GetSpacing()
    origin3 = itk_planar1_resampled.GetOrigin()
    print('spacing3, origin3', spacing3, origin3)

    # center for dimension X
    #center = origin3[0] + size3[0]*spacing3[0]/2.0
    #print('center', center)
    #origin2[0] += center - origin2[0] - size2[0]*spacing2[0]/2.0
    #print('origin2', origin2)
    #itk_planar2.SetOrigin(origin2)

    #itk.imwrite(itk_planar2, 'p2.mhd') ## FIXME

    # MI filter
    f = itk.MattesMutualInformationImageToImageMetric[ImageType, ImageType].New()
    #region = itk.ImageAlgorithm.EnlargeRegionOverBox(itk_planar2.GetLargestPossibleRegion(), itk_planar2, itk_planar1_resampled)
    #print(region)
    interp = itk.NearestNeighborInterpolateImageFunction[ImageType,itk.D].New()
    tmax = size3[1]+size2[1]
    print('tmax', tmax)
    regionM = itk_planar2.GetLargestPossibleRegion()
    regionF = itk_planar1_resampled.GetLargestPossibleRegion()
    print('regions', regionM, regionF)
    region = regionF
    #typedef itk::ImageRegion< Dimension > RegionType;
    #RegionType = type(region)
    #region = RegionType()
    #size = itk.Size[2]()
    #size[0] = size3[0]
    #size[1] = 100
    #region.SetSize(size)
    #print(region)
    #exit(0)

    # thresholdFilter = itk.BinaryThresholdImageFilter[ImageType, ImageType].New()
    # thresholdFilter.SetInput(itk_planar1_resampled)
    # thresholdFilter.SetLowerThreshold(1)
    # thresholdFilter.SetUpperThreshold(1000000)
    # thresholdFilter.SetOutsideValue(0)
    # thresholdFilter.SetInsideValue(1)

    # thresholdFilter.Update()
    # mask = thresholdFilter.GetOutput()
    # itk.imwrite(mask, 'mask.mhd')
    # mf = itk.MaskImageFilter[ImageType].New()
    # mf.SetInsideValue(1)
    # mf.SetMaskImage(mask)
    # mf.Update()
    # mask = mf.GetOutput()
    #smo = itk.ImageMaskSpatialObject[2].New()
    #smo.SetImage(mask)

    # FIXME (assume index = 0)
    #corner = size3+0.5
    #pF = itk_planar1_resampled.TransformContinuousIndexToPhysicalPoint(s)
    #pM = itk_planar2.TransformContinuousIndexToPhysicalPoint(s)
    #print(pF, pM)
    #exit(0)

    print(itk_planar2)
    a = itk_planar2.GetLargestPossibleRegion().GetUpperIndex()
    print('a', a)
    a = itk_planar2.TransformIndexToPhysicalPoint(a)
    print(itk_planar2.GetLargestPossibleRegion())
    print(itk_planar2.GetDirection())
    print(itk_planar2.GetSpacing())
    print(itk_planar2.GetOrigin(), a)

    #itk_planar1_resampled.SetDirection(itk_planar2.GetDirection())
    #print(itk_planar1_resampled)
    b = itk_planar1_resampled.GetLargestPossibleRegion().GetUpperIndex()
    print('b', b)
    b = itk_planar1_resampled.TransformIndexToPhysicalPoint(b)
    print(itk_planar1_resampled.GetLargestPossibleRegion())
    print(itk_planar1_resampled.GetDirection())
    print(itk_planar1_resampled.GetSpacing())
    print(itk_planar1_resampled.GetOrigin(), b)
    #exit(0)

    amin = 99999
    tmin = 0
    for t in range(tmax):
        #print(t)
        origin = np.array(origin2)
        origin[1] = origin2[1] - t*spacing2[1]
        #origin2[1] = origin3[1] - size2[1]*spacing2[1] + t*spacing2[1]
        itk_planar2.SetOrigin(origin)
        # print(origin)
        # print(itk_planar2.GetOrigin())
        # print(itk_planar1_resampled.GetOrigin())

        f.SetMovingImage(itk_planar2)
        f.SetFixedImage(itk_planar1_resampled)

        #f.SetMovingImage(itk_planar1_resampled)
        #f.SetFixedImage(itk_planar2)

        transform = itk.IdentityTransform[itk.D, 2].New()
        transform.SetIdentity()
        f.SetTransform(transform)
        #f.SetFixedImageRegion(itk_planar1_resampled.GetLargestPossibleRegion())
        #f.SetFixedImageRegion(itk_planar2.GetLargestPossibleRegion())
        f.SetFixedImageRegion(region)
        f.SetFixedImageSamplesIntensityThreshold(2)
        f.SetUseFixedImageSamplesIntensityThreshold(True)
        #print(f.GetUseFixedImageSamplesIntensityThreshold())
        #   f.SetFixedImageMask(smo)

        f.SetInterpolator(interp)
        #f.UseAllPixelsOff()
        f.UseAllPixelsOn()
        #f.SetNumberOfSpatialSamples(500)
        f.SetNumberOfHistogramBins(50)
        f.ReinitializeSeed()
        f.Initialize()

        #print('tr=', transform.GetParameters()[0])

        #print(transform.GetParameters())
        #itk.imwrite(itk_planar1_resampled, 'resample.mhd') ## FIXME
        #itk.imwrite(itk_planar2, 'p3.mhd') ## FIXME
        try:
            a = f.GetValue(transform.GetParameters())
        except:
            print('stop')
            t = tmax+1
            a = 999999
            break
        if a<amin:
            amin = a
            tmin = t

        print(t, a)


    # end
    print('end', amin, tmin)
    origin = np.array(origin2)
    origin[1] = origin2[1] - tmin*spacing2[1]
    itk_planar2.SetOrigin(origin)

    #
    print('write image p3')
    itk.imwrite(itk_planar2, 'p3.mhd')
    return itk_planar2, tmin

