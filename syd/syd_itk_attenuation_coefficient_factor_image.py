#!/usr/bin/env python3

import itk
import SimpleITK as sitk
import numpy as np

# -----------------------------------------------------------------------------
def itk_attenuation_correction_factor_image(itk_ct):

    # as np array (warning z is first now)
    arr_ct = itk.GetArrayViewFromImage(itk_ct)

    w = [1.0]
    nb_ene_windows = len(w)

    # CT 60 keV
    act = 0.00022586
    wct = 0.2068007
    bct = 0.57384408

    # In111 245 --> ARRAY FIXME
    asp = 0.0001384
    wsp = 0.12842316
    bsp = 0.22564878

    # init
    acf = np.ones_like(arr_ct)

    # main computation
    for i in range(nb_ene_windows):
        acf = acf + w[i]*np.where(arr_ct>0,
                                  wsp + wct * (bct - wct) * (bsp - wsp) * arr_ct,
                                  wsp + wct * (asp - asp) * arr_ct)

    # remove negative values
    acf = np.clip(acf, 0, None)

    # create the final itk image
    acf = acf.astype(np.float32)
    itk_acf = itk.GetImageFromArray(acf)
    itk_acf.CopyInformation(itk_ct)

    return itk_acf


