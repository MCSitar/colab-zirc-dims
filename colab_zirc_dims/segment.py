# -*- coding: utf-8 -*-
"""
Created on Thu Nov  4 20:15:35 2021

@author: 6600K-PC
"""

import numpy as np
import skimage

from skimage import measure
from skimage import filters
from skimage import exposure
from skimage.morphology import binary_closing

from . import mos_proc

# Get regionated masks from an image via Otsu threshholding
def otsu_masks(input_image):
    """Use Otsu threshholding to segment an image.

    Parameters
    ----------
    input_image : image array
        An input image array. Will be threshholded in grayscale.

    Returns
    -------
    output_masks_list : list[arr]
        A list of mask arrays (one for each region) from Otsu thresholding.

    """
    gray_img = skimage.color.rgb2gray(input_image)
    thresh_val = filters.threshold_otsu(gray_img)
    thresh_img = binary_closing(gray_img > thresh_val)
    label_mask = measure.label(thresh_img.astype(int))
    region_vals = list(np.unique(label_mask))

    #removes very small regions
    larger_region_vals = [val for val in region_vals
                          if np.count_nonzero(label_mask == val) > 100]

    output_masks_list = []
    for each_region in larger_region_vals:
        each_mask = label_mask == each_region
        output_masks_list.append(each_mask)

    return output_masks_list


def segment(curr_mosaic_img, curr_predictor,
            try_bools = [False, False, False, False]):
    """Apply different methods (see try_bools) iteratively to try to segment
       an ALC image.

    Parameters
    ----------
    curr_mosaic_img : MosImg class instance
        A MosImg class instance w/ desired subimage coords already set.
    curr_predictor : Detectron2 Predictor class instance
        A predictor to apply to the subimage extracted.
    try_bools : list[bool], optional
        A list of bools determining what alternate segmentation methods will be
        applied if Detectron2 segmentation of the original image is unsuccesful.
        In order, these are:
        [apply predictor to 0.9x zoomed-out subimg,
         apply predictor to 1.1x zoomed-in subimg,
         apply predictor to histogram-equalized (contrast-enhanced) subimg,
         Otsu threshholding]
        The default is [False, False, False, False].

    Returns
    -------
    mask_found_bool : Boolean
        True or False, depending on whether a central mask was found.
    array or list
        np array for the central mask found. Empty list if none found.

    """
    #original subimage size; used for size manipulations
    orig_subimg_size = curr_mosaic_img.sub_img_size_input

    #apply predictor to given subimg
    central_mask = mos_proc.get_central_mask(curr_predictor(curr_mosaic_img.sub_img))

    # try zooming out slightly
    if try_bools[0] and not central_mask[0]:
        print('Trying segementation of zoomed-out subimage')
        curr_mosaic_img.set_sub_img_size(round(orig_subimg_size * 1.1))
        central_mask = mos_proc.get_central_mask(curr_predictor(curr_mosaic_img.sub_img))
        curr_mosaic_img.set_sub_img_size(orig_subimg_size)
    #try zooming in slightly
    if try_bools[1] and not central_mask[0]:
        print('Trying segementation of zoomed-in subimage')
        curr_mosaic_img.set_sub_img_size(round(orig_subimg_size * 0.9))
        central_mask = mos_proc.get_central_mask(curr_predictor(curr_mosaic_img.sub_img))
        curr_mosaic_img.set_sub_img_size(orig_subimg_size)
    #try increasing contrast
    if try_bools[2] and not central_mask[0]:
        print('Trying segmentation of contrast-enhanced subimage')
        cont_enhanced = exposure.equalize_hist(curr_mosaic_img.sub_img)
        central_mask = mos_proc.get_central_mask(curr_predictor(cont_enhanced))
    #try otsu threshholding
    if try_bools[3] and not central_mask[0]:
        print('Trying Otsu threshholding')
        central_mask = mos_proc.get_central_mask(otsu_masks(curr_mosaic_img.sub_img))
    return central_mask

def gen_segment(curr_img, curr_predictor,
                try_bools = [False, False]):
    """Apply different methods (see try_bools) iteratively to try to segment
       a single shot (non-ALC) image. Because image source is not a mosaic,
       extent jittering (zooming in and out) is not available.

    Parameters
    ----------
    curr_img : np array
        An array representing an image for segmentation.
    curr_predictor : Detectron2 Predictor class instance
        A predictor to apply to the subimage extracted.
    try_bools : list[bool], optional
        A list of bools determining what alternate segmentation methods will be
        applied if Detectron2 segmentation of the original image is unsuccesful.
        In order, these are:
        [apply predictor to histogram-equalized (contrast-enhanced) subimg,
         Otsu threshholding]
        The default is [False, False].

    Returns
    -------
    mask_found_bool : Boolean
        True or False, depending on whether a central mask was found.
    array or list
        np array for the central mask found. Empty list if none found.

    """

    #apply predictor to given subimg
    central_mask = mos_proc.get_central_mask(curr_predictor(curr_img))

    #try increasing contrast
    if try_bools[0] and not central_mask[0]:
        print('Trying segmentation of contrast-enhanced subimage')
        cont_enhanced = exposure.equalize_hist(curr_img)
        central_mask = mos_proc.get_central_mask(curr_predictor(cont_enhanced))
    #try otsu threshholding
    if try_bools[1] and not central_mask[0]:
        print('Trying Otsu threshholding')
        central_mask = mos_proc.get_central_mask(otsu_masks(curr_img))
    return central_mask