#!/usr/bin/env python3

import syd
import itk

# -----------------------------------------------------------------------------
def faf_calibration(db, planar, spect, ct, options):
    '''
    TODO
    '''

    print('planar', planar)
    print('spect', spect)
    print('ct', ct)
    print('options', options)

    # options
    # store intermediate images: yes
    # tags intermediate images

    # read images
    itk_planar = syd.read_itk_image(db, planar)

    # Step0: crop vial from planar
    if 'crop_y' in options:
        itk_planar = syd.itk_crop_planar(itk_planar, options['crop_y'])
        tags = ['crop_y']
        planar = syd.insert_write_new_image(db, planar, itk_planar, tags)

    # Step1: compute GM image


    # Step2: compute ACF image (3D) Attenuation Correction Factor
    # sydFAF_ACF_Image
    # flip option ?

    # Step3: register SPECT and Planar
    # sydFAF_RegisterPlanarImages
    # flip option ?

    # Step4: compute gm_acf (2D) = GM x ACF
    # sydFAF_ACGM_Image

    # Step5: crop and FAF mask ; calibration

