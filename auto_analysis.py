import sys
from pathlib import Path
from statistics import mean, median, pstdev, stdev
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.ticker import PercentFormatter
import nibabel as nib

# add as arg? add mask arg?
POLYFIT = True
KTRANS_MIN_THRESHOLD = 0.00001

def analyze(file_dir):
    # load files from script pipeline
    files = ['/T1_wm.nii.gz', '/T1_gm.nii.gz', '/T1_csf.nii.gz', '/Ktrans_wm.nii.gz',
            '/Ktrans_gm.nii.gz', '/Ktrans_csf.nii.gz', '/15_wm_mask_dyn.nii.gz', '/15_gm_mask_dyn.nii.gz']
    for i, file in enumerate(files):
        files[i] = file_dir + file

    T1_wm = nib.load(files[0])
    T1_gm = nib.load(files[1])
    # T1_csf = nib.load(files[2])
    Ktrans_wm = nib.load(files[3])
    Ktrans_gm = nib.load(files[4])
    # Ktrans_csf = nib.load(files[5])
    wm_mask = nib.load(files[6])
    gm_mask = nib.load(files[7])

    # load data from files
    T1_wm_data = T1_wm.get_fdata()
    T1_gm_data = T1_gm.get_fdata()
    # T1_csf_data = T1_csf.get_fdata()
    Ktrans_wm_data = Ktrans_wm.get_fdata()
    Ktrans_gm_data = Ktrans_gm.get_fdata()
    # Ktrans_csf_data = Ktrans_csf.get_fdata()
    wm_data = wm_mask.get_fdata()
    gm_data = gm_mask.get_fdata()

    mri_shape = T1_wm_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])

    # initialize arrays
    T1_wm_mean = []
    T1_gm_mean = []
    # T1_csf_mean = []
    T1_wm_median = []
    T1_gm_median = []
    # T1_csf_median = []
    T1_wm_zeros = []
    T1_gm_zeros = []

    Ktrans_wm_mean = []
    Ktrans_gm_mean = []
    # Ktrans_csf_mean = []
    Ktrans_wm_median = []
    Ktrans_gm_median = []
    # Ktrans_csf_median = []
    Ktrans_wm_zeros = []
    Ktrans_gm_zeros = []

    # get mean/median of each matter slice
    for i in range(slice_num):
        a = np.where(T1_wm_data[:, :, i] > 0)
        # must check for empty slices
        if a[0].size > 0:
            T1_wm_mean.append(T1_wm_data[:, :, i][a].mean())
        else:
            T1_wm_mean.append(0)

        a = np.where(T1_gm_data[:, :, i] > 0)
        if a[0].size > 0:
            T1_gm_mean.append(T1_gm_data[:, :, i][a].mean())
        else:
            T1_gm_mean.append(0)

        # a = np.where(T1_csf_data[:, :, i] > 0)
        # if a[0].size > 0:
        #     T1_csf_mean.append(T1_csf_data[:, :, i][a].mean())
        # else:
        #     T1_csf_mean.append(0)

        a = np.where(T1_wm_data[:, :, i] > 0)
        if a[0].size > 0:
            T1_wm_median.append(median(T1_wm_data[:, :, i][a]))
        else:
            T1_wm_median.append(0)

        a = np.where(T1_gm_data[:, :, i] > 0)
        if a[0].size > 0:
            T1_gm_median.append(median(T1_gm_data[:, :, i][a]))
        else:
            T1_gm_median.append(0)

        # a = np.where(T1_csf_data[:, :, i] > 0)
        # if a[0].size > 0:
        #     T1_csf_median.append(median(T1_csf_data[:, :, i][a]))
        # else:
        #     T1_csf_median.append(0)
        
        
        a = np.where(Ktrans_wm_data[:, :, i] > KTRANS_MIN_THRESHOLD)
        if a[0].size > 0:
            Ktrans_wm_mean.append(Ktrans_wm_data[:, :, i][a].mean())
        else:
            Ktrans_wm_mean.append(0)
        
        a = np.where(Ktrans_gm_data[:, :, i] > KTRANS_MIN_THRESHOLD)
        if a[0].size > 0:
            Ktrans_gm_mean.append(Ktrans_gm_data[:, :, i][a].mean())
        else:
            Ktrans_gm_mean.append(0)

        # a = np.where(Ktrans_csf_data[:, :, i] > KTRANS_MIN_THRESHOLD)
        # if a[0].size > 0:
        #     Ktrans_csf_mean.append(Ktrans_csf_data[:, :, i][a].mean())
        # else:
        #     Ktrans_csf_mean.append(0)
        
        a = np.where(Ktrans_wm_data[:, :, i] > KTRANS_MIN_THRESHOLD)
        if a[0].size > 0:
            Ktrans_wm_median.append(median(Ktrans_wm_data[:, :, i][a]))
        else:
            Ktrans_wm_median.append(0)

        a = np.where(Ktrans_gm_data[:, :, i] > KTRANS_MIN_THRESHOLD)
        if a[0].size > 0:
            Ktrans_gm_median.append(median(Ktrans_gm_data[:, :, i][a]))
        else:
            Ktrans_gm_median.append(0)

        # a = np.where(Ktrans_csf_data[:, :, i] > KTRANS_MIN_THRESHOLD)
        # if a[0].size > 0:
        #     Ktrans_csf_median.append(median(Ktrans_csf_data[:, :, i][a]))
        # else:
        #     Ktrans_csf_median.append(0)

        a = np.where((wm_data[:, :, i] > 0) & (T1_wm_data[:, :, i] <= KTRANS_MIN_THRESHOLD))
        if a[0].size > 0:
            T1_wm_zeros.append(len(T1_wm_data[:, :, i][a]) / len(T1_wm_data[:, :, i][wm_data[:, :, i] > 0]) * 100)
        else:
            T1_wm_zeros.append(0)

        a = np.where((gm_data[:, :, i] != 0) & (T1_gm_data[:, :, i] <= KTRANS_MIN_THRESHOLD))
        if a[0].size > 0:
            T1_gm_zeros.append(len(T1_gm_data[:, :, i][a])  / len(T1_gm_data[:, :, i][gm_data[:, :, i] > 0]) * 100)
        else:
            T1_gm_zeros.append(0)

        a = np.where((wm_data[:, :, i] > 0) & (Ktrans_wm_data[:, :, i] <= KTRANS_MIN_THRESHOLD))
        if a[0].size > 0:
            Ktrans_wm_zeros.append(len(Ktrans_wm_data[:, :, i][a]) / len(Ktrans_wm_data[:, :, i][wm_data[:, :, i] > 0]) * 100)
        else:
            Ktrans_wm_zeros.append(0)
        
        a = np.where((gm_data[:, :, i] > 0) & (Ktrans_gm_data[:, :, i] <= KTRANS_MIN_THRESHOLD))
        if a[0].size > 0:
            Ktrans_gm_zeros.append(len(Ktrans_gm_data[:, :, i][a]) / len(Ktrans_gm_data[:, :, i][wm_data[:, :, i] > 0]) * 100)
        else:
            Ktrans_gm_zeros.append(0)

    # Figure city
    n_bins = 500
    fig, ((ax0, ax1), (ax2, ax3)) = plt.subplots(2, 2, figsize=(20, 6))

    ## Initialize values
    T1_wm_data = T1_wm_data.flatten()
    T1_gm_data = T1_gm_data.flatten()
    T1_wm_median_truncated = median(T1_wm_data[np.where(np.logical_and(T1_wm_data > 0, T1_wm_data < 4000))])
    T1_gm_median_truncated = median(T1_gm_data[np.where(np.logical_and(T1_gm_data > 0, T1_gm_data < 4000))])

    Ktrans_wm_data = Ktrans_wm_data.flatten()
    Ktrans_gm_data = Ktrans_gm_data.flatten()
    # Ktrans_csf_data = Ktrans_csf_data.flatten()
    Ktrans_wm_median_truncated = median(Ktrans_wm_data[Ktrans_wm_data > KTRANS_MIN_THRESHOLD])
    Ktrans_gm_median_truncated = median(Ktrans_gm_data[Ktrans_gm_data > KTRANS_MIN_THRESHOLD])
    Ktrans_wm_stdev_truncated = stdev(Ktrans_wm_data[Ktrans_wm_data > KTRANS_MIN_THRESHOLD])
    Ktrans_gm_stdev_truncated = stdev(Ktrans_gm_data[Ktrans_gm_data > KTRANS_MIN_THRESHOLD])

    # for i in range(slice_num)
    #     T1_wm_zeros = size(T1_wm_data[T1_wm_data[:,:,i] == 0])
    #     T1_gm_zeros = size(T1_gm_data[T1_gm_data[:,:,i] == 0])
    #
    #     Ktrans_wm_zeros = size(Ktrans_wm_data[Ktrans_wm_data == 0])
    #     Ktrans_gm_zeros = size(Ktrans_gm_data[Ktrans_gm_data == 0])
    
    ## T1 Histogram
    ax0.set_xlabel('T1')
    ax0.set_ylabel('Frequency')
    # ax0.set_ylim([0, 2700])
    wmn, wmins, wmpatches = ax0.hist(T1_wm_data, n_bins, range=(10, 4000), histtype='bar', color='pink', label="wm")
    gmn, gmins, gmpatches = ax0.hist(T1_gm_data, n_bins, range=(10, 4000), histtype='bar', alpha=0.9, color='gray', label='gm')
    # ax0.hist(T1_csf_data, n_bins, range=(10, 4000), histtype='bar', color = 'cyan', label = 'csf')
    ax0.axvline(T1_wm_median_truncated, color='lightpink', linestyle='dashed')
    ax0.axvline(T1_gm_median_truncated, color='gray', linestyle='dashed')
    # ax0.axvline(mean(T1_csf_data[T1_csf_data > 0]), color = 'cyan', linestyle = 'dashed')
    min_ylim, max_ylim = ax0.get_ylim()
    ax0.legend()
    # FWHMs
    ## wm
    wm_median_bindex = (np.abs(wmins - T1_wm_median_truncated)).argmin()
    wm_top10 = np.argpartition(wmn, -10)[-10:]
    wm_halfmax = mean(wmn[wm_top10])/2
    wm_lower_i = (np.abs(wmn[0:wm_median_bindex] - wm_halfmax)).argmin()
    lower = wmins[wm_lower_i]
    ax0.axvline(lower, color='lightpink', linestyle='dotted')
    wm_upper_i = (np.abs(wmn[wm_median_bindex:n_bins+1] - wm_halfmax)).argmin()+wm_median_bindex
    # print((np.abs(wmn[250:501] - wm_halfmax)).argmin()+250)
    upper = wmins[wm_upper_i]
    ax0.axvline(upper, color='lightpink', linestyle='dotted')
    ax0.hlines(wm_halfmax, wmins[wm_lower_i], wmins[wm_upper_i], color='k')
    ## gm
    gm_median_bindex = (np.abs(gmins - T1_gm_median_truncated)).argmin()
    gm_top10 = np.argpartition(gmn, -10)[-10:]
    gm_halfmax = mean(gmn[gm_top10])/2
    gm_lower_i = (np.abs(gmn[0:gm_median_bindex] - gm_halfmax)).argmin()
    lower = gmins[gm_lower_i]
    ax0.axvline(lower, color='gray', linestyle='dotted')
    gm_upper_i = (np.abs(gmn[gm_median_bindex:n_bins+1] - gm_halfmax)).argmin()+gm_median_bindex
    # print((np.abs(gmn[0:250] - gm_halfmax)).argmin())
    upper = gmins[gm_upper_i]
    ax0.axvline(upper, color='gray', linestyle='dotted')
    ax0.hlines(gm_halfmax, gmins[gm_lower_i], gmins[gm_upper_i], color='k')
    ax0.text(wmins[wm_lower_i]*.1, max_ylim*0.9, 'Median: {:.1f}'.format(T1_wm_median_truncated), color='pink')
    ax0.text(gmins[gm_upper_i]*1.04, max_ylim*0.9, 'Median: {:.1f}'.format(T1_gm_median_truncated), color='gray')
    ax0.text(wmins[wm_lower_i]*.1, max_ylim*0.8, 'stdev: {:.1f}'.format(pstdev(T1_wm_data[np.where(np.logical_and(T1_wm_data > 0, T1_wm_data < 4000))])), color='pink')
    ax0.text(gmins[gm_upper_i]*1.04, max_ylim*0.8, 'stdev: {:.1f}'.format(pstdev(T1_gm_data[np.where(np.logical_and(T1_gm_data > 0, T1_gm_data < 4000))])), color='gray')
    ax0.text(wmins[wm_lower_i]*.1, wm_halfmax*1, 'FWHM: {:.1f}'.format(wmins[wm_upper_i]-wmins[wm_lower_i]), color='k')
    ax0.text(gmins[gm_upper_i]*1.04, gm_halfmax*1, 'FWHM: {:.1f}'.format(gmins[gm_upper_i]-gmins[gm_lower_i]), color='k')


    ## Ktrans histogram
    ax1.set_xlabel('Ktrans')
    ax1.set_ylabel('Frequency')
    # ax1.set_ylim([0, 1400])
    ax1.hist(Ktrans_gm_data, n_bins, range=(KTRANS_MIN_THRESHOLD, .02), histtype='bar', alpha=1, color='gray', label='gm')
    ax1.hist(Ktrans_wm_data, n_bins, range=(KTRANS_MIN_THRESHOLD, .02), histtype='bar', alpha=0.9, color='pink', label='wm')
    # ax1.hist(Ktrans_csf_data, n_bins, range=(KTRANS_MIN_THRESHOLD, .02), histtype='bar', alpha=0.4, color = 'cyan', label = 'csf')
    _, max_ylim = ax1.get_ylim()
    ax1.axvline(Ktrans_wm_median_truncated, color='pink', linestyle='dashed')
    ax1.axvline(Ktrans_gm_median_truncated, color='gray', linestyle='dashed')
    ax1.text(Ktrans_wm_median_truncated*.1, max_ylim*0.2, 'Median: {:.5f}'.format(Ktrans_wm_median_truncated), color='whitesmoke')
    ax1.text(Ktrans_gm_median_truncated*1.1, max_ylim*0.9, 'Median: {:.5f}'.format(Ktrans_gm_median_truncated), color='gray')
    ax1.text(Ktrans_wm_median_truncated*.1, max_ylim*0.1, 'stdev: {:.5f}'.format(Ktrans_wm_stdev_truncated), color='whitesmoke')
    ax1.text(Ktrans_gm_median_truncated*1.1, max_ylim*0.8, 'stdev: {:.5f}'.format(Ktrans_gm_stdev_truncated), color='gray')
    # ax1.axvline(mean(Ktrans_csf_data[Ktrans_csf_data > 0]), color = 'cyan', linestyle = 'dashed')
    ax1.legend()

    ## T1 medians plot
    ax2.set_xlabel('Slice #')
    ax2.set_ylabel('T1 Medians')
    ax2.set_ylim([0, 2200])
    ax2.plot(range(slice_num), T1_wm_median, label='wm', color='pink')
    ax2.plot(range(slice_num), T1_gm_median, label='gm', color='gray')
    # ax2.plot(range(slice_num), T1_csf_mean, label = 'csf', color = 'cyan')
    ax2.grid()
    ax2.legend()

    ## Ktrans medians plot
    ax3.set_xlabel('Slice #')
    ax3.set_ylabel('Ktrans Medians')
    ax3.set_ylim([0, 0.017])
    ax3.plot(range(slice_num), Ktrans_wm_median, label='wm', color='pink')
    ax3.plot(range(slice_num), Ktrans_gm_median, label='gm', color='gray')
    # ax3.plot(range(slice_num), Ktrans_csf_mean, label = 'csf', color = 'cyan')
    ax3.grid()
    ax3.legend()

    # Save graphs
    path2 = file_dir + '/T1_Ktrans_analysis.png'
    plt.savefig(path2)
    # Zeros
    fig2, ((ax4, ax5)) = plt.subplots(2, 1, figsize=(20,6))

    ## T1 zeros plot
    ax4.set_xlabel('Slice #')
    ax4.set_ylabel('T1 Zeros')
    # ax4.set_ylim([0, 0.017])
    ax4.plot(range(slice_num), T1_wm_zeros, label='wm', color='pink')
    ax4.plot(range(slice_num), T1_gm_zeros, label='gm', color='gray')
    # ax3.plot(range(slice_num), Ktrans_csf_mean, label = 'csf', color = 'cyan')
    ax4.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax4.grid()
    ax4.legend()

    ## Ktrans zeros plot
    ax5.set_xlabel('Slice #')
    ax5.set_ylabel('Ktrans Zeros')
    # ax4.set_ylim([0, 0.017])
    ax5.plot(range(slice_num), Ktrans_wm_zeros, label='wm', color='pink')
    ax5.plot(range(slice_num), Ktrans_gm_zeros, label='gm', color='gray')
    # ax3.plot(range(slice_num), Ktrans_csf_mean, label = 'csf', color = 'cyan')
    ax5.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax5.grid()
    ax5.legend()

    plt.savefig(file_dir + '/T1_Ktrans_zeros.png')
    print(file_dir)


dir = Path(sys.argv[1])     # takes timepoint directory as argument
analyze(str(dir))
