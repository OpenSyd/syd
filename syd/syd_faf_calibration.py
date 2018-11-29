#!/usr/bin/env python3

import syd
import itk

# -----------------------------------------------------------------------------
def faf_calibration(db, planar, spect, ct, options):
    '''
    TODO
    '''

    # options:
    # store intermediate images: yes
    # tags intermediate images
    # k for geom mean ?
    save = options['save_intermediate_images']

    # read images
    itk_planar = syd.read_itk_image(db, planar)

    # Step0: crop vial from planar
    print(options)
    if 'crop_y' in options:
        itk_planar = syd.itk_crop_planar(itk_planar, options['crop_y'])
        if save:
            planar = syd.insert_write_new_image(db, planar, itk_planar, ['crop_y'])
            print(planar)

    # Step1: compute GM image
    itk_gm = syd.itk_geometrical_mean(itk_planar, k=1.1)
    if save:
        gm = syd.insert_write_new_image(db, planar, itk_gm, ['geometrical_mean'])
        print(gm)

    # Step2: compute ACF image (3D) Attenuation Correction Factor
    # sydFAF_ACF_Image
    # flip option ?
    itk_ct = syd.read_itk_image(db, ct)
    itk_acf = syd.itk_attenuation_correction_factor_image(itk_ct)
    if save:
        acf = dict(ct)
        acf['pixel_unit'] = "mu"
        acf['pixel_type'] = "float"
        acf = syd.insert_write_new_image(db, acf, itk_acf, ['acf'])
        print(acf)

    # Step3: register SPECT and Planar
    # sydFAF_RegisterPlanarImages
    # flip option ?

    # Step4: compute gm_acf (2D) = GM x ACF
    # sydFAF_ACGM_Image

    # Step5: crop and FAF mask ; calibration

