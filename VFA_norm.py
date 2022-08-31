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
    img1 = nib.load(mri_file1)
    img2 = nib.load(wm_masked)
    num = int(re.search(r'\d+', mri_file1.split('/')[-1]).group())
    img_data1 = img1.get_fdata()
    wm_data = img2.get_fdata()
    img_shape = img_data1.shape
    wm_shape = wm_data.shape
    slice_num = min(img_shape[0], img_shape[1], img_shape[2])
    slice_loc = img_shape.index(slice_num)
    img_data1 = np.reshape(img_data1, (img_shape[min(dim-set([slice_loc]))], img_shape[max(dim-set([slice_loc]))], slice_num))
    wm_data = np.reshape(wm_data, (wm_shape[min(dim-set([slice_loc]))], wm_shape[max(dim-set([slice_loc]))], slice_num))
    data = []
    orig_img = []
    
    # get mean of each wm slice and each orig slice
    for i in range(slice_num):
        a = np.where(wm_data[:, :, i] > 0)
        data.append(wm_data[:, :, i][a].mean())
        a = np.where(img_data1[:, :, i] > 0)
        orig_img.append(img_data1[:, :, i][a].mean())

    slice_index = []
    img_data2 = img_data1
    wm2 = wm_data
    
    # apply normalizations
    if POLYFIT is True:
        print("Using Polynomial fitting to normalize")
        poly_norm_curve = Polynomial.fit(list(range(slice_num)), data, 4)
        norm_slices = polyval(list(range(slice_num)), poly_norm_curve.convert().coef)
        
        # apply scaling factor
        for i in range(slice_num):
            norm_val1 = norm_slices[i] / mean(norm_slices)
            img_data2[:,:,i] /= norm_val1
            wm2[:,:,i] /= norm_val1
            
    else:
        print("Using Z-normalization")
        # calc stats of all slices
        data_mean = mean(data[1:13])
        std_dev = pstdev(data[1:13])
        err = 1*std_dev
        # find slices out of range
        min_val = data_mean - err
        max_val = data_mean + err
        
        for i in range (slice_num):
            if not (min_val <= data[i] <= max_val):
                slice_index.append(i)
        
        for i in slice_index:    
            norm_val1 = img_data1[:, :, i] * (data_mean/data[i])
            img_data2[:, :, i] = norm_val1
    
    norm_img = []
    norm_wm = []
    for i in range(slice_num):
        a = np.where(img_data2[:, :, i] > 0)
        norm_img.append(img_data2[:, :, i][a].mean())
        a = np.where(wm2[:, :, i] > 0)
        norm_wm.append(wm2[:, :, i][a].mean())
        
    data_mean1 = mean(norm_img)

    fig, ax = plt.subplots(figsize=(20, 6))
    ax.plot(range(slice_num), data, '-ok',  label='orig')
    ax.plot(range(slice_num), norm_slices, ':ob', label='fit')
    ax.plot(range(slice_num), norm_wm, '--og', label='corrected')
    ax.set_xlabel('Slice #')
    ax.set_ylabel('White Matter Mean')
    ax.set_title("VFA Slice Normalization")
    ax.legend();

    path2 = file_dir + '/' + str(num) +'_BFC_Z.png'   #THE STRING IN THE END CONTAINS THE FILE NAME OF THE GRAPHS GENERATED
    plt.savefig(path2)
    
    img_data2 = np.reshape(img_data2, img_shape)
    final_img = nib.Nifti1Image(img_data2, img1.affine)
    path3 = file_dir + '/' + str(num) + '_BFC_Z.nii'  #THE STRING IN THE END CONTAINS THE FILE NAME OF THE NORMALIZED NIFTI IMAGE GENERATED
    nib.save(final_img, path3)


print(sys.argv[1])
dir = Path(sys.argv[1])     # takes timepoint directory as argument
files_in_dir = dir.iterdir()
for file in files_in_dir:
    if str(file).endswith('_bfc.nii'):
        file1 = str(file)
        print(file1)
        mask_file = file1.split('.', 1)
        mask_file = mask_file[0] + '_wm.' + mask_file[1] + '.gz'
        
        normalize(file1, mask_file, str(dir))   #CALLING THE 'normalize()' FUNCTION TO PERFORM THE NORMALIZATION
