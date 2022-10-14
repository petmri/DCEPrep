import sys
from pathlib import Path
import re
from statistics import mean, pstdev
import numpy as np
# import numpy.polynomial.polynomial as poly
import matplotlib
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial
from numpy.polynomial.polynomial import polyval
import nibabel as nib
matplotlib.use('Agg')

# add as arg? add mask arg?
POLYFIT = False

def normalize(mri_file1, wm_masked, file_dir):   # THE FUNCTION PERFORMING THE NORMALIZATION
    dim = {0, 1, 2}
    mri = nib.load(mri_file1)
    white_matter = nib.load(wm_masked)
    num = int(re.search(r'\d+', mri_file1.split('/')[-1]).group())
    mri_data = mri.get_fdata()
    wm_data = white_matter.get_fdata()
    mri_shape = mri_data.shape
    wm_shape = wm_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])
    slice_loc = mri_shape.index(slice_num)
    mri_data = np.reshape(mri_data, (mri_shape[min(dim-set([slice_loc]))], mri_shape[max(dim-set([slice_loc]))], slice_num))
    wm_data = np.reshape(wm_data, (wm_shape[min(dim-set([slice_loc]))], wm_shape[max(dim-set([slice_loc]))], slice_num))
    wm_mean = []
    orig_img = []

    total_wm_voxels = wm_data[wm_data > 0].size
    polyfit_slice_weights = []

    # get mean of each wm slice and each orig slice
    for i in range(slice_num):
        a = np.where(wm_data[:, :, i] > 0)
        polyfit_slice_weights.append(wm_data[:, :, i][a].size/total_wm_voxels)
        if a[0].size > 0:
            wm_mean.append(wm_data[:, :, i][a].mean())
        else:
            wm_mean.append(0)
        a = np.where(mri_data[:, :, i] > 0)
        if a[0].size > 0:
            orig_img.append(mri_data[:, :, i][a].mean())
        else:
            orig_img.append(0)

    slice_index = []
    mri_final = mri_data
    wm_final = wm_data

    # apply normalizations
    if POLYFIT is True:
        print("Using Polynomial fitting to normalize")
        poly_norm_curve = Polynomial.fit(list(range(slice_num)), wm_mean, 4, w=polyfit_slice_weights)
        norm_slices = polyval(list(range(slice_num)), poly_norm_curve.convert().coef)

        # apply scaling factor
        for i in range(slice_num):
            norm_val1 = norm_slices[i] / mean(norm_slices)
            mri_final[:, :, i] /= norm_val1
            wm_final[:, :, i] /= norm_val1

    else:
        print("Using Z-normalization")
        # calc stats of all slices
        data_mean = mean(wm_mean[0:slice_num-1])
        std_dev = pstdev(wm_mean[0:slice_num-1])
        err = 0.1*std_dev
        # find slices out of range
        min_val = data_mean - err
        max_val = data_mean + err

        for i in range(slice_num):
            if not min_val <= wm_mean[i] <= max_val:
                slice_index.append(i)

        for i in slice_index:
            norm_val1 = mri_data[:, :, i] * (data_mean/wm_mean[i])
            mri_final[:, :, i] = norm_val1
            wm_final[:, :, i] = wm_data[:, :, i] * (data_mean/wm_mean[i])

    norm_img = []
    norm_wm = []
    for i in range(slice_num):
        a = np.where(mri_final[:, :, i] > 0)
        if a[0].size > 0:
            norm_img.append(mri_final[:, :, i][a].mean())
        else:
            norm_img.append(0)
        a = np.where(wm_final[:, :, i] > 0)
        if a[0].size > 0:
            norm_wm.append(wm_final[:, :, i][a].mean())
        else:
            norm_wm.append(0)

    # data_mean1 = mean(norm_img)

    fig, ax = plt.subplots(figsize=(20, 6))
    ax.plot(range(slice_num), wm_mean, '-ok', label='original')
    if POLYFIT is True:
        ax.plot(range(slice_num), norm_slices, ':ob', label='fit')
    ax.plot(range(slice_num), norm_wm, '--og', label='corrected')
    ax.set_xlabel('Slice #')
    ax.set_ylabel('White Matter Mean')
    ax.set_title("VFA Slice Normalization")
    ax.legend()

    path2 = file_dir + '/' + str(num) +'_BFC_Z.png'
    plt.savefig(path2)

    mri_final = np.reshape(mri_final, mri_shape)
    final_img = nib.Nifti1Image(mri_final, mri.affine)
    path3 = file_dir + '/' + str(num) + '_BFC_Z.nii'
    nib.save(final_img, path3)


dir = Path(sys.argv[1])     # takes timepoint directory as argument
files_in_dir = dir.iterdir()
for file in files_in_dir:
    if re.search(r'\d+_bfc.nii.*', str(file)):
        file1 = str(file)
        mask_file = file1.split('.', 1)
        mask_file = mask_file[0] + '_wm.nii'

        try:
            normalize(file1, mask_file, str(dir))   #CALLING THE 'normalize()' FUNCTION TO PERFORM THE NORMALIZATION
        except FileNotFoundError:
            normalize(file1, mask_file + ".gz", str(dir))
