import os
import sys
import numpy as np
# import numpy.polynomial.polynomial as poly
import matplotlib
from numpy.polynomial import Polynomial
from numpy.core.fromnumeric import shape
from numpy.polynomial.polynomial import polyfit, polyval
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nibabel as nib
from scipy import ndimage
from PIL import Image
from statistics import mean, pstdev
from pathlib import Path
import re

# add as arg? add mask arg?
POLYFIT = True

def normalize(mri_file1, wm_masked, file_dir):   # THE FUNCTION PERFORMING THE NORMALIZATION
    dim = {0,1,2}
    mri = nib.load(mri_file1)
    wm_mask = nib.load(wm_masked)
    # num = int(re.search(r'\d+', mri_file1.split('/')[-1]).group())
    mri_data = mri.get_fdata()
    wm_data = wm_mask.get_fdata()
    mri_shape = mri_data.shape
    wm_shape = wm_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])
    slice_loc = mri_shape.index(slice_num)
    mri_data = np.reshape(mri_data, (mri_shape[min(dim-set([slice_loc]))], mri_shape[max(dim-set([slice_loc]))], slice_num, 64))
    wm_data = np.reshape(wm_data, (wm_shape[min(dim-set([slice_loc]))], wm_shape[max(dim-set([slice_loc]))], slice_num, 64))
    wm_mean = []
    orig_img = []
    
    # get mean of each wm slice and each orig slice
    for i in range(slice_num):
        a = np.where(wm_data[:, :, i, :] > 0)
        wm_mean.append(wm_data[:, :, i, :][a].mean())
        a = np.where(mri_data[:, :, i, :] > 0)
        orig_img.append(mri_data[:, :, i, :][a].mean())

    slice_index = []
    mri_final = mri_data
    wm2 = wm_data
    
    # apply normalizations
    if POLYFIT is True:
        print("Using Polynomial fitting to normalize " + mri_file1)
        poly_norm_curve = Polynomial.fit(list(range(slice_num)), wm_mean, 4)
        norm_slices = polyval(list(range(slice_num)), poly_norm_curve.convert().coef)
        
        # apply scaling factor
        for i in range(slice_num):
            scaling_factor = norm_slices[i] / mean(norm_slices)
            mri_final[:, :, i, :] /= scaling_factor
            wm2[:, :, i, :] /= scaling_factor
            
    else:
        print("Using Z-normalization")
        # calc stats of all slices
        data_mean = mean(wm_mean[1:13])
        std_dev = pstdev(wm_mean[1:13])
        err = 1*std_dev
        # find slices out of range
        min_val = data_mean - err
        max_val = data_mean + err
        
        for i in range (slice_num):
            if not (min_val <= wm_mean[i] <= max_val):
                slice_index.append(i)
        
        for i in slice_index:    
            norm_val1 = mri_data[:, :, i, :] * (data_mean/wm_mean[i])
            mri_final[:, :, i, :] = norm_val1
    
    norm_img = []
    norm_wm = []
    for i in range(slice_num):
        a = np.where(mri_final[:, :, i, :] > 0)
        norm_img.append(mri_final[:, :, i, :][a].mean())
        a = np.where(wm2[:, :, i, :] > 0)
        norm_wm.append(wm2[:, :, i, :][a].mean())
        
    data_mean1 = mean(norm_img)

    fig, ax = plt.subplots(figsize=(20, 6))
    ax.plot(range(slice_num), wm_mean, '-ok',  label='orig')
    ax.plot(range(slice_num), norm_slices, ':ob', label='fit')
    ax.plot(range(slice_num), norm_wm, '--og', label='corrected')
    ax.set_xlabel('Slice #')
    ax.set_ylabel('White Matter Mean')
    ax.set_title("DCE Slice Normalization")
    ax.legend();

    path2 = file_dir +'/DCE_mc_bfc_norm.png'   #THE STRING IN THE END CONTAINS THE FILE NAME OF THE GRAPHS GENERATED
    plt.savefig(path2)
    print(file_dir)
    mri_final = np.reshape(mri_final, mri_shape)
    final_img = nib.Nifti1Image(mri_final, mri.affine)
    path3 = file_dir + '/DCE_mc_bfc_norm.nii'  #THE STRING IN THE END CONTAINS THE FILE NAME OF THE NORMALIZED NIFTI IMAGE GENERATED
    nib.save(final_img, path3)


print(sys.argv[1])
dir = Path(sys.argv[1])     # takes timepoint directory as argument
files_in_dir = dir.iterdir()
for file in files_in_dir:
    if str(file).endswith('mc_bfc.nii'):
        file1 = str(file)
        mask_file = file1.split('.', 1)
        mask_file = mask_file[0] + '_wm.' + mask_file[1] + '.gz'
        
        normalize(file1, mask_file, str(dir))   #CALLING THE 'normalize()' FUNCTION TO PERFORM THE NORMALIZATION
