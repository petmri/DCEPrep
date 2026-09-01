import sys
import os
from pathlib import Path
from statistics import mean, pstdev, median
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial
from numpy.polynomial.polynomial import polyval
import nibabel as nib
from lmfit import Model

matplotlib.use('Agg')

# add as arg? add mask arg?
GAUSSFIT = True
POLYFIT = True
SAVE_HIST_PLOTS = True


def double_gaussian(x, A1, mu1, sigma1, A2, mu2, sigma2):
    return (
        A1 * np.exp(-0.5 * ((x - mu1) / sigma1) ** 2) +
        A2 * np.exp(-0.5 * ((x - mu2) / sigma2) ** 2)
    )


DOUBLE_GAUSSIAN_MODEL = Model(double_gaussian)


def positive_slice_means(data):
    positive_mask = data > 0
    counts = positive_mask.sum(axis=(0, 1, 3), dtype=np.int64)
    sums = np.where(positive_mask, data, 0).sum(axis=(0, 1, 3), dtype=np.float64)
    return np.divide(sums, counts, out=np.zeros_like(sums, dtype=np.float64), where=counts > 0), counts


def apply_slice_scale(data, scale_factors):
    return data * scale_factors[np.newaxis, np.newaxis, :, np.newaxis]

def normalize(mri_file1, wm_masked, file_dir):   # THE FUNCTION PERFORMING THE NORMALIZATION
    mri = nib.load(mri_file1)
    wm_mask = nib.load(wm_masked)
    mri_data = np.asarray(mri.dataobj, dtype=np.float32)
    wm_data = np.asarray(wm_mask.dataobj, dtype=np.float32)
    mri_shape = mri_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])
    axis_order = np.argsort([mri_shape[0], mri_shape[1], mri_shape[2]])
    # Unpack the axis order
    # usual shape should be x >= y > z
    z_index, y_index, x_index = axis_order
    # if x and y are the same, swap them
    if mri_shape[x_index] == mri_shape[y_index]:
        x_index, y_index = y_index, x_index
    transpose_axes = (x_index, y_index, z_index, 3)
    inverse_axes = tuple(np.argsort(transpose_axes[:3])) + (3,)
    mri_data = np.transpose(mri_data, transpose_axes)
    wm_data = np.transpose(wm_data, transpose_axes)

    wm_mean, wm_counts = positive_slice_means(wm_data)
    total_wm_voxels = int(wm_counts.sum())
    if total_wm_voxels > 0:
        polyfit_slice_weights = wm_counts / total_wm_voxels
    else:
        polyfit_slice_weights = np.zeros(slice_num, dtype=np.float64)

    slice_index = []
    mri_final = mri_data.copy()
    wm_final = wm_data.copy()

    gaussian_params = [0 for i in range(slice_num)]
    hist_dir = Path(file_dir).parent / 'figures' / 'hist'
    if SAVE_HIST_PLOTS:
        hist_dir.mkdir(parents=True, exist_ok=True)

    if GAUSSFIT:
        startat = 0
        endat = slice_num
        hadSuccess = False
        # get histogram of each wm slice
        for i in range(slice_num):
            slice_values = wm_data[:, :, i, :]
            positive_values = slice_values[slice_values > 0]
            area = positive_values.size

            # Initial guess for the parameters
            # count voxels within 1 std of mean
            amp_guess = 0
            params = None
            # check if slice is empty
            if area == 0:
                if hadSuccess and i < endat:
                    endat = i
                elif not hadSuccess:
                    startat = i + 1
                continue

            hist, bins = np.histogram(positive_values, bins=100)
            bin_width = bins[1] - bins[0]
            slice_std = positive_values.std()
            if slice_std == 0:
                continue

            hadSuccess = True
            slice_median = np.median(positive_values)
            amp_guess = area / slice_std * 0.3989 * bin_width
            params = DOUBLE_GAUSSIAN_MODEL.make_params(
                A1=amp_guess * 0.1,
                mu1=wm_mean[i],
                sigma1=slice_std,
                A2=amp_guess,
                mu2=slice_median,
                sigma2=slice_std,
            )
            result = DOUBLE_GAUSSIAN_MODEL.fit(hist, params, x=bins[:-1])
            gaussian_params[i] = result.best_values

            if SAVE_HIST_PLOTS:
                plt.figure()
                plt.bar(bins[:-1], hist, width=np.diff(bins), align='edge', alpha=0.5)
                plt.plot(bins[:-1], result.best_fit, color='red', linewidth=2)
                plt.title(f"Histogram and Fitted Curve - Slice {i+1}")
                plt.xlabel("Pixel Value")
                plt.ylabel("Frequency")
                plt.savefig(hist_dir / f'DCE_{i + 1}_hist.png')
                plt.close()

        # apply normalizations
        print("Using Gaussian fitting to normalize DCE")
        mu = np.zeros(slice_num, dtype=np.float32)
        for i in range(startat, endat):
            if gaussian_params[i]['A1'] > gaussian_params[i]['A2'] and gaussian_params[i]['mu1'] > 0 and gaussian_params[i]['mu1'] > gaussian_params[i]['mu2'] and gaussian_params[i]['mu1'] < 1500:
                mu[i] = gaussian_params[i]['mu1']
            else:
                mu[i] = gaussian_params[i]['mu2']

        valid_mu = mu[mu > 0]
        median_mu = float(np.median(valid_mu)) if valid_mu.size > 0 else 1.0
        scale_factors = np.where(mu > 0, median_mu / mu, 1.0).astype(np.float32)
        mri_final = apply_slice_scale(mri_final, scale_factors)
        wm_final = apply_slice_scale(wm_final, scale_factors)

    elif POLYFIT is True:
        print("Using Polynomial fitting to normalize " + mri_file1)
        poly_norm_curve = Polynomial.fit(list(range(slice_num)), wm_mean, 4, w=polyfit_slice_weights)
        norm_slices = polyval(list(range(slice_num)), poly_norm_curve.convert().coef)

        # apply scaling factor
        mean_norm = mean(norm_slices)
        scale_factors = np.divide(norm_slices, mean_norm, out=np.ones_like(norm_slices, dtype=np.float64), where=mean_norm != 0)
        mri_final = apply_slice_scale(mri_final, 1.0 / scale_factors)
        wm_final = apply_slice_scale(wm_final, 1.0 / scale_factors)

    else:
        print("Using Z-normalization")
        # calc stats of all slices
        data_mean = mean(wm_mean[0:slice_num-1])
        std_dev = pstdev(wm_mean[0:slice_num-1])
        err = .5*std_dev
        # find slices out of range
        min_val = data_mean - err
        max_val = data_mean + err

        for i in range(slice_num):
            if not min_val <= wm_mean[i] <= max_val:
                slice_index.append(i)

        for i in slice_index:
            norm_val1 = mri_data[:, :, i, :] * (data_mean/wm_mean[i])
            mri_final[:, :, i, :] = norm_val1
            wm_final[:, :, i, :] = norm_val1
            
    norm_wm, _ = positive_slice_means(wm_final)

    fig, ax = plt.subplots(figsize=(20, 6))
    ax.plot(range(slice_num), wm_mean, '-ok', label='original')
    if POLYFIT is True and GAUSSFIT is False:
        ax.plot(range(slice_num), norm_slices, ':ob', label='fit')
    if GAUSSFIT:
        ax.plot(range(slice_num), mu, 'o', label='mu', color='grey')
        ax.plot(range(slice_num), np.ones(slice_num)*median_mu, ':x', label='median_mu', color='lightgreen')
    ax.plot(range(slice_num), norm_wm, '--xg', label='corrected')
    ax.set_xlabel('Slice #')
    ax.set_ylabel('White Matter Mean')
    ax.set_title("DCE Slice Normalization")
    ax.legend()

    path2 = 'figures/' + mri_file1.split('desc-bfc_DCE')[0].split('/')[-1] + 'desc-bfcz_DCE.svg'   #THE STRING IN THE END CONTAINS THE FILE NAME OF THE GRAPHS GENERATED
    plt.savefig(path2, bbox_inches='tight')
    plt.close()

    mri_final = np.transpose(mri_final, inverse_axes)
    mri_final = mri_final.astype(np.float32)
    final_img = nib.Nifti1Image(mri_final, mri.affine)
    path3 = mri_file1.split('desc-bfc_DCE')[0] + 'desc-bfcz_DCE.nii'  #THE STRING IN THE END CONTAINS THE FILE NAME OF THE NORMALIZED NIFTI IMAGE GENERATED
    nib.save(final_img, path3)


dir = Path(sys.argv[1])     # takes timepoint directory as argument
files_in_dir = dir.iterdir()
for file in files_in_dir:
    if str(file).endswith('desc-bfc_DCE.nii') or str(file).endswith('desc-bfc_DCE.nii.gz'):
        file1 = str(file)
        mask_file = file1.split('desc-bfc_DCE', 1)[0]
        mask_file = mask_file + 'label-WM_DCE.nii'

        if Path(mask_file + ".gz").exists():
            mask_file += ".gz"
        elif not Path(mask_file).exists():
            print(f"Mask file not found for {file1}")
            continue

        try:
            normalize(file1, mask_file, str(dir))
        except Exception as e:
            print(e)
            print("Error in normalizing " + file1)
