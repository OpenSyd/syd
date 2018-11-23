#!/usr/bin/env python3

import itk
import syd

# -----------------------------------------------------------------------------
def stitch_image(db, image1, image2):

    print('image1', image1)
    print('image2', image2)
    filename1 = syd.get_image_filename(db, image1)
    filename2 = syd.get_image_filename(db, image2)
    im1 = itk.imread(filename1)
    im2 = itk.imread(filename2)

    im = stitch_itk_image(im1, im2)

    print('TODO: insert an image')
    return im


# -----------------------------------------------------------------------------
def stitch_itk_image(im1, im2):
    # FIXME -> to put in a external file itk related

    # check image size and type
    # FIXME

    # create an image
    ImageType = type(im1)
    print(ImageType)
    image = ImageType.New()

    # get sizes
    region1 = im1.GetLargestPossibleRegion()
    region2 = im2.GetLargestPossibleRegion()
    a1 = im1.TransformIndexToPhysicalPoint(region1.GetIndex())
    b1 = im1.TransformIndexToPhysicalPoint(region1.GetSize())
    a2 = im2.TransformIndexToPhysicalPoint(region2.GetIndex())
    b2 = im2.TransformIndexToPhysicalPoint(region2.GetSize())
    print(a1, b1)
    print(a2, b2)

    # create new size
    za = min(a1[2], a2[2], b1[2], b2[2])
    zb = max(a1[2], a2[2], b1[2], b2[2])

    # swap if decreasing coordinates
    if (a1[2]>b1[2]):
        zb,za = za,zb
    a = a1
    a[2] = za
    b = b1
    b[2] = zb
    print(a, b)


    return image


