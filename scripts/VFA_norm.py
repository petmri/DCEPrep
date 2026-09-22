import sys
from pathlib import Path
import re
from statistics import mean, pstdev, median
import numpy as np
# import numpy.polynomial.polynomial as poly
import matplotlib
import matplotlib.pyplot as plt
import multiprocessing
from numpy.polynomial import Polynomial
from numpy.polynomial.polynomial import polyval
import nibabel as nib
from scipy.optimize import curve_fit
from lmfit import Model
matplotlib.use('Agg')

# add as arg? add mask arg?
GAUSSFIT = True
POLYFIT = True

def normalize(mri_file1, wm_masked, file_dir):   # THE FUNCTION PERFORMING THE NORMALIZATION
    dim = {0, 1, 2}
    mri = nib.load(mri_file1)
    white_matter = nib.load(wm_masked)
    num = int(re.search(r'flip-(\d+)', mri_file1.split('/')[-1]).group(1))
    num = f"{num:02d}"
    mri_data = mri.get_fdata()
    wm_data = white_matter.get_fdata()
    mri_shape = mri_data.shape
    wm_shape = wm_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])
    axis_order = np.argsort([mri_shape[0], mri_shape[1], mri_shape[2]])
    # Unpack the axis order
    # usual shape should be x >= y > z
    z_index, y_index, x_index = axis_order
    # if x and y are the same, swap them
    if mri_shape[x_index] == mri_shape[y_index]:
        x_index, y_index = y_index, x_index
    mri_data = np.transpose(mri_data, (x_index, y_index, z_index))
    wm_data = np.transpose(wm_data, (x_index, y_index, z_index))
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

    gaussian_params = [0 for i in range(slice_num)]
    if GAUSSFIT:
        startat = 0
        endat = slice_num
        hadSuccess = False
        # get histogram of each wm slice
        for i in range(slice_num):
            # print("SLICE: " + str(i + 1))
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

            # prepare for gaussian fitting
            bin_width = bins[1] - bins[0]
            model = Model(double_gaussian)
            amp_guess = 0
            params = 0
            # check if slice is empty
            if area < 1000 or pstdev(wm_data[:,:,i][a]) == 0:
                # just get from next slice
                # if i == slice_num - 1:
                #     a = np.where(wm_data[:,:,i-1] > 0)
                #     area = np.count_nonzero(wm_data[:,:,i-1][a])
                #     amp_guess = area / pstdev(wm_data[:,:,i-1][a]) * 0.3989 * bin_width
                #     params = model.make_params(A1=amp_guess*0.1, mu1=wm_mean[i-1], sigma1=pstdev(wm_data[:,:,i-1][a]), A2=amp_guess, mu2=median(wm_data[:,:,i-1][a]), sigma2=pstdev(wm_data[:,:,i-1][a]))
                # else:
                #     a = np.where(wm_data[:,:,i+1] > 0)
                #     area = np.count_nonzero(wm_data[:,:,i+1][a])
                #     amp_guess = area / pstdev(wm_data[:,:,i+1][a]) * 0.3989 * bin_width
                #     params = model.make_params(A1=amp_guess*0.1, mu1=wm_mean[i+1], sigma1=pstdev(wm_data[:,:,i+1][a]), A2=amp_guess, mu2=median(wm_data[:,:,i+1][a]), sigma2=pstdev(wm_data[:,:,i+1][a]))
                # omit slice if empty
                # if i == 0:
                #     startat = 1
                # elif i == slice_num - 1:
                #     endat = slice_num - 2
                # continue
                if hadSuccess and i < endat:
                    endat = i
                elif not hadSuccess:
                    startat = i + 1
                continue
            else:
                hadSuccess = True
                amp_guess = area / pstdev(wm_data[:,:,i][a]) * 0.3989 * bin_width
                params = model.make_params(A1=amp_guess*0.1, mu1=wm_mean[i], sigma1=pstdev(wm_data[:,:,i][a]), A2=amp_guess, mu2=median(wm_data[:,:,i][a]), sigma2=pstdev(wm_data[:,:,i][a]))

            result = model.fit(hist, params, x=bins[:-1])
            # print(result.fit_report())
            # print(result.best_values)
            gaussian_params[i] = result.best_values

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
            hist_dir = file_dir + '/../figures/hist'
            Path(hist_dir).mkdir(parents=True, exist_ok=True)

            # Save the figure
            path1 = file_dir + '/../figures/hist/' + str(num) + '_' + str(i+1) + '_hist.png'
            plt.savefig(path1)
            plt.close()


        # apply normalizations
        print("Using Gaussian fitting to normalize FA " + str(num))
        mu = [0 for i in range(slice_num)]
        # print(startat, endat)
        # endat = len(gaussian_params)
        for i in range(startat, endat):
            # max(gaussian_params[i][0], gaussian_params[i][3])
            # if gaussian_params[i][0] > gaussian_params[i][3] and gaussian_params[i][1] > 0 and gaussian_params[i][1] < 1000:# and abs(gaussian_params[i][1] - wm_mean[i]) < abs(gaussian_params[i][4] - wm_mean[i]):
            #     mu.append(gaussian_params[i][1])
            # else:
            #     mu.append(gaussian_params[i][4])
            # print(i, slice_num)
            if gaussian_params[i]['A1'] > gaussian_params[i]['A2'] and gaussian_params[i]['mu1'] > 0 and gaussian_params[i]['mu1'] > gaussian_params[i]['mu2'] and gaussian_params[i]['mu1'] < 1500:
                mu[i] = gaussian_params[i]['mu1']
            else:
                mu[i] = gaussian_params[i]['mu2']

            # print("mu " + str(mu[i]))
            # print("SLICE: " + str(i + 1))
            # print("mu1 and mu2: " + str(gaussian_params[i]['mu1']) + " " + str(gaussian_params[i]['mu2']))
            # print("A: " + str(gaussian_params[i]['A1']) + " " + str(gaussian_params[i]['A2']))
            # print("sigma: " + str(gaussian_params[i]['sigma1']) + " " + str(gaussian_params[i]['sigma2']))

        median_mu = median([m for m in mu if m != 0])
        # print("median_mu: " + str(median_mu))
        for i in range(slice_num):
            if mu[i] == 0:
                continue
            scale_factor = median_mu / mu[i]
            mri_final[:, :, i] *= scale_factor
            wm_final[:, :, i] *= scale_factor

    elif POLYFIT is True:
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
        err = 1*std_dev
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
    if POLYFIT is True and GAUSSFIT is False:
        ax.plot(range(slice_num), norm_slices, ':ob', label='fit')
    ax.plot(range(slice_num), norm_wm, '--xg', label='corrected', mfc='none')
    if GAUSSFIT:
        ax.plot(range(slice_num), mu, 'o', label='mu', color='grey')
        ax.plot(range(slice_num), np.ones(slice_num)*median_mu, ':x', label='median_mu', color='lightgreen')
    ax.set_xlabel('Slice #')
    ax.set_ylabel('White Matter Mean')
    ax.set_title("VFA Slice Normalization")
    ax.legend()

    # if figures directory doesn't exist, create it
    Path('figures').mkdir(parents=True, exist_ok=True)

    path2 = 'figures/' + str(prefix) + '_flip-' + str(num) + '_space-DCEref_desc-bfcz_VFA.svg'
    plt.savefig(path2, bbox_inches='tight')
    plt.close()

    # transpose mri_final back to mri_shape order
    x_index = mri_final.shape.index(mri_shape[0])
    y_index = mri_final.shape.index(mri_shape[1])
    z_index = mri_final.shape.index(mri_shape[2])
    if x_index == y_index:
        y_index = set(dim) - {x_index, z_index}
        y_index = list(y_index)[0]
    elif x_index == z_index:
        z_index = set(dim) - {x_index, y_index}
        z_index = list(z_index)[0]
    elif y_index == z_index:
        z_index = set(dim) - {x_index, y_index}
        z_index = list(z_index)[0]

    mri_final = np.transpose(mri_final, (x_index, y_index, z_index))
    mri_final = mri_final.astype(np.float32)
    # cut off z-slices where mu is 0
    # mri_final = mri_final[:, :, startat:endat]
    final_img = nib.Nifti1Image(mri_final, mri.affine)
    path3 = file_dir + '/' + str(prefix) + '_flip-' + str(num) + '_space-DCEref_desc-bfcz_VFA.nii.gz'
    nib.save(final_img, path3)

if __name__ == "__main__":
    dir = Path(sys.argv[1])     # takes timepoint directory as argument
    prefix = sys.argv[2]
    BFC = sys.argv[3]
    file_pattern = r'.*flip-\d+_space-DCEref_desc-bfc_VFA.nii.*' if BFC else r'.*flip-\d+_space-DCEref_label-brain_VFA.nii.*'
    files_in_dir = dir.iterdir()
    file_list = [file for file in files_in_dir if re.search(r'.*flip-\d+_space-DCEref_label-brain_VFA.nii.*', str(file))]
    num_processes = len(file_list)

    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.starmap(normalize, [(str(file), str(file).split('_label-brain', 1)[0] + '_label-WM_VFA.nii.gz', str(dir)) for file in file_list])
