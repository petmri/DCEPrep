import sys
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

def normalize(mri_file1, wm_masked, file_dir):   # THE FUNCTION PERFORMING THE NORMALIZATION
    dim = {0, 1, 2}
    mri = nib.load(mri_file1)
    wm_mask = nib.load(wm_masked)
    mri_data = mri.get_fdata()
    wm_data = wm_mask.get_fdata()
    mri_shape = mri_data.shape
    wm_shape = wm_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])
    z_index = mri_shape.index(slice_num)
    x_index = mri_shape.index(max(mri_shape[0], mri_shape[1], mri_shape[2]))
    y_index = mri_shape[1:3].index(max(0, mri_shape[1], mri_shape[2])) + 1
    mri_data = np.transpose(mri_data, (x_index, y_index, z_index, 3))
    wm_data = np.transpose(wm_data, (x_index, y_index, z_index, 3))
    wm_mean = []
    orig_img = []

    total_wm_voxels = wm_data[wm_data > 0].size
    polyfit_slice_weights = []

    # get mean of each wm slice and each orig slice
    for i in range(slice_num):
        a = np.where(wm_data[:, :, i, :] > 0)
        polyfit_slice_weights.append(wm_data[:, :, i, :][a].size/total_wm_voxels)
        if a[0].size > 0:
            wm_mean.append(wm_data[:, :, i, :][a].mean())
        else:
            wm_mean.append(0)

        a = np.where(mri_data[:, :, i, :] > 0)
        if a[0].size > 0:
            orig_img.append(mri_data[:, :, i, :][a].mean())
        else:
            orig_img.append(0)

    slice_index = []
    mri_final = mri_data
    wm_final = wm_data

    gaussian_params = []
    if GAUSSFIT:
        # get histogram of each wm slice
        for i in range(slice_num):
            a = np.where(wm_data[:, :, i] > 0)
            hist, bins = np.histogram(wm_data[:,:,i][a].flatten(), bins=100)

            def double_gaussian(x, A1, mu1, sigma1, A2, mu2, sigma2):
                return (
                    A1 * np.exp(-0.5 * ((x - mu1) / sigma1) ** 2) +
                    A2 * np.exp(-0.5 * ((x - mu2) / sigma2) ** 2)
                )

            # Initial guess for the parameters
            # count voxels within 1 std of mean
            area = np.count_nonzero(wm_data[:,:,i][a])
            # get bin width
            bin_width = bins[1] - bins[0]
            amp_guess = area / pstdev(wm_data[:,:,i][a]) * 0.3989 * bin_width
                    
            model = Model(double_gaussian)
            params = model.make_params(A1=amp_guess*0.1, mu1=wm_mean[i], sigma1=pstdev(wm_data[:,:,i][a]), A2=amp_guess, mu2=median(wm_data[:,:,i][a]), sigma2=pstdev(wm_data[:,:,i][a]))
            result = model.fit(hist, params, x=bins[:-1])
            gaussian_params.append(result.best_values)

            # Plot the histogram
            plt.figure()
            plt.bar(bins[:-1], hist, width=np.diff(bins), align='edge', alpha=0.5)

            # Plot the fitted curve
            plt.plot(bins[:-1], result.best_fit, color='red', linewidth=2)

            # Add labels and title
            plt.title(f"Histogram and Fitted Curve - Slice {i+1}")
            plt.xlabel("Pixel Value")
            plt.ylabel("Frequency")

            # make hist directory if it doesn't exist
            hist_dir = file_dir + '/figures/hist'
            Path(hist_dir).mkdir(parents=True, exist_ok=True)

            # Save the figure
            path1 = file_dir + '/figures/hist/DCE_' + str(i+1) + '_hist.png'
            plt.savefig(path1)
            plt.close()

        # apply normalizations
        print("Using Gaussian fitting to normalize DCE")
        mu = []
        for i in range(slice_num):            
            if gaussian_params[i]['A1'] > gaussian_params[i]['A2']:
                mu.append(gaussian_params[i]['mu1'])
            else:
                mu.append(gaussian_params[i]['mu2'])
            # print("mu " + str(mu[i]))
            # print("SLICE: " + str(i + 1))
            # print("mu: " + str(gaussian_params[i]['mu1']) + " " + str(gaussian_params[i]['mu2']))
            # print("A: " + str(gaussian_params[i]['A1']) + " " + str(gaussian_params[i]['A2']))
            # print("sigma: " + str(gaussian_params[i]['sigma1']) + " " + str(gaussian_params[i]['sigma2']))

        mean_mu = mean(mu)
        for i in range(slice_num):
            scale_factor = mean_mu / mu[i]
            mri_final[:, :, i] *= scale_factor
            wm_final[:, :, i] *= scale_factor

    elif POLYFIT is True:
        print("Using Polynomial fitting to normalize " + mri_file1)
        poly_norm_curve = Polynomial.fit(list(range(slice_num)), wm_mean, 4, w=polyfit_slice_weights)
        norm_slices = polyval(list(range(slice_num)), poly_norm_curve.convert().coef)

        # apply scaling factor
        for i in range(slice_num):
            scaling_factor = norm_slices[i] / mean(norm_slices)
            mri_final[:, :, i, :] /= scaling_factor
            wm_final[:, :, i, :] /= scaling_factor

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
            

    norm_img = []
    norm_wm = []
    for i in range(slice_num):
        a = np.where(mri_final[:, :, i, :] > 0)
        if a[0].size > 0:
            norm_img.append(mri_final[:, :, i, :][a].mean())
        else:
            norm_img.append(0)

        a = np.where(wm_final[:, :, i, :] > 0)
        if a[0].size > 0:
            norm_wm.append(wm_final[:, :, i, :][a].mean())
        else:
            norm_wm.append(0)

    data_mean1 = mean(norm_img)

    fig, ax = plt.subplots(figsize=(20, 6))
    ax.plot(range(slice_num), wm_mean, '-ok', label='original')
    if POLYFIT is True and GAUSSFIT is False:
        ax.plot(range(slice_num), norm_slices, ':ob', label='fit')
    if GAUSSFIT:
        ax.plot(range(slice_num), mu, 'o', label='mu', color='grey')
        ax.plot(range(slice_num), np.ones(slice_num)*mean_mu, ':x', label='mean_mu', color='lightgreen')
    ax.plot(range(slice_num), norm_wm, '--xg', label='corrected')
    ax.set_xlabel('Slice #')
    ax.set_ylabel('White Matter Mean')
    ax.set_title("DCE Slice Normalization")
    ax.legend()

    path2 = file_dir +'/figures/DCE_mc_bfc_norm.svg'   #THE STRING IN THE END CONTAINS THE FILE NAME OF THE GRAPHS GENERATED
    plt.savefig(path2, bbox_inches='tight')

    mri_final = np.transpose(mri_final, (x_index, y_index, z_index, 3))
    final_img = nib.Nifti1Image(mri_final, mri.affine)
    path3 = file_dir + '/DCE_mc_bfc_norm.nii'  #THE STRING IN THE END CONTAINS THE FILE NAME OF THE NORMALIZED NIFTI IMAGE GENERATED
    nib.save(final_img, path3)


dir = Path(sys.argv[1])     # takes timepoint directory as argument
files_in_dir = dir.iterdir()
for file in files_in_dir:
    if str(file).endswith('mc_bfc.nii') or str(file).endswith('mc_bfc.nii.gz'):
        file1 = str(file)
        mask_file = file1.split('.', 1)
        mask_file = mask_file[0] + '_wm.nii'

        try:
            normalize(file1, mask_file + ".gz", str(dir))
        except FileNotFoundError:
            normalize(file1, mask_file, str(dir))
        except Exception as e:
            print(e)
            print("Error in normalizing " + file1)
