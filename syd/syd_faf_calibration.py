#!/usr/bin/env python3

import syd
import itk
import numpy as np

# -----------------------------------------------------------------------------
def faf_calibration(db, planar, spect, ct, options):
    '''
    TODO
    '''

    # how to organise ? seperate fct ?
    # write all only at the end ? 

    # options:
    # store intermediate images: yes
    # tags intermediate images
    # k for geom mean ?
    save = options['save_intermediate_images']
    if not 'axe' in options:
        options['axe'] = 1

    verbose = True

    print('Options', options, save)

    # read images
    itk_planar = syd.read_itk_image(db, planar)

    # Step: crop vial from planar
    if 'crop_y' in options:
        if verbose: print('Step: crop planar image')
        itk_planar = syd.itk_crop_planar(itk_planar, options['crop_y'])
        if save:
            planar = syd.insert_write_new_image(db, planar, itk_planar, ['crop_y'])
            print(planar)

    # Step: compute GM image
    if verbose: print('Step: geometrical mean')
    itk_gm = syd.itk_geometrical_mean(itk_planar, k=1.1)
    if save:
        gm = syd.insert_write_new_image(db, planar, itk_gm, ['geometrical_mean'])
        print(gm)

    # Step: project SPECT to planar
    if verbose: print('Step: project SPECT in 2D')
    itk_spect = syd.read_itk_image(db, spect)
    itk_projected_spect = syd.itk_projection_image(itk_spect, options['axe'])
    if save:
        proj_spect = dict(planar)
        syd.rm_tag(proj_spect, 'geometrical_mean')
        syd.rm_tag(proj_spect, 'planar')
        syd.rm_tag(proj_spect, 'crop_y')
        syd.add_tag(proj_spect, 'spect')
        syd.add_tag(proj_spect, 'projected')
        proj_spect = syd.insert_write_new_image(db, proj_spect, itk_projected_spect)
        syd.dump(proj_spect)

    # Step: register SPECT and Planar
    if verbose: print('Step: register planar with projected SPECT')
    itk_gm_reg, offset = syd.itk_register_planar_images(itk_projected_spect, itk_gm)
    if save:
        gm_reg = dict(gm)
        syd.add_tag(gm_reg, 'register')
        syd.add_tag(gm_reg, 'offset_'+str(offset))
        gm_reg = syd.insert_write_new_image(db, gm_reg, itk_gm_reg)
        print('Registration offset: ', offset)
        syd.dump(proj_spect)

    # Step: compute ACF image (3D) Attenuation Correction Factor
    # flip option ?
    if verbose: print('Step: building ACF from CT')
    itk_ct = syd.read_itk_image(db, ct)
    itk_acf = syd.itk_attenuation_correction_factor_image(itk_ct)
    if save:
        acf = dict(ct)
        acf['pixel_unit'] = "mu"
        acf['pixel_type'] = "float"
        acf = syd.insert_write_new_image(db, acf, itk_acf, ['acf'])
        syd.dump(acf)

    # DEBUG save
    itk.imwrite(itk_gm_reg, "gm.mhd")
    itk.imwrite(itk_acf, "acf.mhd")

    # Step: compute gm_acf (2D) = GM x ACF
    # sydFAF_ACGM_Image
    # project acf
    # flip 
    # threshold FIXME
    # exponential 
    # resample ?
    # If the attenuation is <0, set it to 0

    print('clamp values >0')
    data = itk.GetArrayViewFromImage(itk_acf)
    print('min = ', np.min(data))
    np.clip(data, 0, None)
    print('min = ', np.min(data))

    itk_proj_acf = syd.itk_projection_image(itk_acf, options['axe'])
    if options['flip_acf']:
        itk_proj_acf = syd.itk_flip_image(itk_proj_acf, 1)

    
        
    if save:
        proj_acf = dict(acf)
        syd.add_tag(proj_acf, 'projected')
        proj_acf = syd.insert_write_new_image(db, proj_acf, itk_proj_acf)
        syd.dump(proj_acf)

    if verbose: print('Step: compute ACF x GM (attenuation corrected gm)')


    # Step5: crop and FAF mask ; calibration

