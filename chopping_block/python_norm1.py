import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nibabel as nib
from scipy import ndimage
from PIL import Image
from statistics import mean, pstdev
from pathlib import Path
import re

def normalize(mri_file1, file_dir):   # THE FUNCTION PERFORMING THE NORMALIZATION
    dim = {0,1,2}
    img1 = nib.load(mri_file1)
    num = int(re.search(r'\d+', mri_file1.split('/')[-1]).group())
    img_data1 = img1.get_fdata()
    img_shape = img_data1.shape
    slice_num = min(img_shape[0], img_shape[1], img_shape[2])
    slice_loc = img_shape.index(slice_num)
    img_data1 = np.reshape(img_data1, (img_shape[min(dim-set([slice_loc]))], img_shape[max(dim-set([slice_loc]))], slice_num))
    data = []
    for i in range(slice_num):
        a = np.where(img_data1[:, :, i] > 0)
        data.append(img_data1[:, :, i][a].mean())
    data_mean = mean(data[1:13])
    std_dev = pstdev(data[1:13])
    err = 1*std_dev
    slice_index = []
    min_val = data_mean - err
    max_val = data_mean + err
    for i in range (slice_num):
        if not (min_val <= data[i] <= max_val):
            slice_index.append(i)
    img_data2 = img_data1

    for i in slice_index:    
        norm_val1 = img_data1[:, :, i] * (data_mean/data[i])
        img_data2[:, :, i] = norm_val1

    data1 = []
    for i in range(slice_num):
        a = np.where(img_data2[:, :, i] > 0)
        data1.append(img_data2[:, :, i][a].mean())
    data_mean1 = mean(data1)

    fig, (ax1, ax2) = plt.subplots(1, 2, sharex = True, sharey=True, figsize=(20,6))
    ax1.plot(data, 'o-', ms=4)
    ax1.grid()
    ax2.plot(data1, 'o-', ms=4)
    ax2.grid()
    path2 = file_dir + '/' + str(num) +'_corr_finalZ.png'   #THE STRING IN THE END CONTAINS THE FILE NAME OF THE GRAPHS GENERATED (I HAVE KEPT IT AS 2_Z.png/5_Z.png/10_Z.png/12_Z.png/15_Z.png AS OF NOW). FOR EACH SUBJECT, THIS FILE GENERATED IS STORED AT THE SAME LOCATION AS THE INPUT FILES
    plt.savefig(path2)
    
    img_data2 = np.reshape(img_data2, img_shape)
    final_img = nib.Nifti1Image(img_data2, img1.affine)
    path3 = file_dir + '/' + str(num) + '_corr_finalZ.nii'  #THE STRING IN THE END CONTAINS THE FILE NAME OF THE NORMALIZED NIFTI IMAGE GENERATED (I HAVE KEPT IT AS 2_Z.nii/5_Z.nii/10_Z.nii/12_Z.nii/15_Z.nii AS OF NOW). FOR EACH SUBJECT, THIS FILE GENERATED IS STORED AT THE SAME LOCATION AS THE INPUT FILES
    nib.save(final_img, path3)
    
    
dir1 = Path(os.getcwd())    # CODE TO AUTOMATICALLY PERFORM THIS NORMALIZATION ON ALL SUBJECTS' ALL VFAs IN THIS DIRECTORY
files_in_dir1 = dir1.iterdir()
for file in files_in_dir1:
    if (os.path.isdir(str(file))):
        files_in_dir2 = file.iterdir()
        for item in files_in_dir2:
            if ((str(item).split('/')[-1] == '1st_timepoint') or (str(item).split('/')[-1] == '2nd_timepoint')):   #SEARCHES FOR THE FOLDERS WITH THESE SPECIFIC NAMES (ENCLOSED IN STRINGS)
                files_in_dir3 = item.iterdir()
                for b1_imgs in files_in_dir3:
                    if str(b1_imgs).endswith('_bfc.nii'):
                        normalize(str(b1_imgs), str(item))   #CALLING THE 'normalize()' FUNCTION TO PERFORM THE NORMALIZATION
