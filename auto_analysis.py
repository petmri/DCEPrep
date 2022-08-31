import os
import sys
import numpy as np
# import numpy.polynomial.polynomial as poly
import matplotlib
from numpy.polynomial import Polynomial
from numpy.core.fromnumeric import shape
from numpy.polynomial.polynomial import polyfit, polyval
from networkx.algorithms.bipartite.basic import density
from keyrings.alt import file
from importlib.metadata import files
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

def analyze(img_files, file_dir):   # THE FUNCTION PERFORMING THE NORMALIZATION
    dim = {0,1,2}
    wm = nib.load(img_files[0])
    gm = nib.load(img_files[1])
    csf = nib.load(img_files[2])
    # norm_img = nib.load(norm_file)
    # num = int(re.search(r'\d+', img_files.split('/')[-1]).group())
    # matter = 
    wm_data = wm.get_fdata()
    # norm_data = norm_img.get_fdata()
    mri_shape = wm_data.shape
    # norm_shape = norm_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])
    slice_loc = mri_shape.index(slice_num)
    # wm_data = np.reshape(wm_data, (mri_shape[min(dim-set([slice_loc]))], mri_shape[max(dim-set([slice_loc]))], slice_num))
    # norm_data = np.reshape(norm_data, (norm_shape[min(dim-set([slice_loc]))], norm_shape[max(dim-set([slice_loc]))], slice_num))
    # norm_mean = []
    orig_mean = []
   

    # get mean of each wm slice and each orig slice
    # for i in range(slice_num):
    #     a = np.where(wm_data[:, :, i] > 0)
    #     orig_mean.append(wm_data[:, :, i][a].mean())
    #     a = np.where(norm_data[:, :, i] > 0)
    #     norm_mean.append(norm_data[:, :, i][a].mean())

    print(mri_shape)

    slice_index = []
    mri_final = wm_data
    # wm2 = norm_data
    

    # fig, ax = plt.subplots(figsize=(20, 6))
    # ax.plot(range(slice_num), wm_data, '-ok',  label='original')
    # ax.plot(range(slice_num), norm_data, '--og', label='corrected')
    # ax.set_xlabel('Slice #')
    # ax.set_ylabel('White Matter Mean')
    # ax.set_title("DCE Slice Normalization")
    # ax.legend();
    n_bins = 500
    fig, ax = plt.subplots(figsize=(20,6))
    wm_data = np.reshape(wm_data, (320*320*14))
    # a = np.where(wm_data > 0)
    # test = wm_data[a]
    print(shape(wm_data[wm_data > 10]))
    ax.hist(wm_data[wm_data > 10], n_bins, range=(0, 4000), density = True, histtype='bar')
    # ax.plot(range(slice_num), orig_mean)
    # plt.show()

    path2 = file_dir + '/DCE_analysis' + '.png'   #THE STRING IN THE END CONTAINS THE FILE NAME OF THE GRAPHS GENERATED
    plt.savefig(path2)
    print(file_dir)


dir = Path(sys.argv[1])     # takes timepoint directory as argument
files_in_dir = dir.iterdir()
files = []
for file in files_in_dir:
    # if re.search(r'T1_(wm)|(gm)|(csf)', file) or re.search(r'Ktrans', file):
        # files.append(file)
    if (str(file).endswith('T1_wm.nii.gz')):
        # files.append(str(file))
        files.append(str(file))
        files.append(str(dir) + '/T1_gm.nii.gz')
        files.append(str(dir) + '/T1_csf.nii.gz')
        analyze(files, str(dir))   #CALLING THE 'normalize()' FUNCTION TO PERFORM THE NORMALIZATION        
    elif (str(file).endswith('Ktrans_wm.nii.gz')):
        files.append(str(file))
        files.append(str(dir) + '/Ktrans_gm.nii.gz')
        files.append(str(dir) + '/Ktrans_csf.nii.gz')
        analyze(files, str(dir))   #CALLING THE 'normalize()' FUNCTION TO PERFORM THE NORMALIZATION
