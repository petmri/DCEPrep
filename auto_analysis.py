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

def analyze(file_dir):
    # load files from script pipeline
    files = ['/T1_wm.nii.gz', '/T1_gm.nii.gz', '/T1_csf.nii.gz', '/Ktrans_wm.nii.gz', '/Ktrans_gm.nii.gz', '/Ktrans_csf.nii.gz']
    for i, file in enumerate(files):
        files[i] = file_dir + file

    dim = {0,1,2}
    T1_wm = nib.load(files[0])
    T1_gm = nib.load(files[1])
    T1_csf = nib.load(files[2])
    Ktrans_wm = nib.load(files[3])
    Ktrans_gm = nib.load(files[4])
    Ktrans_csf = nib.load(files[5])

    # load data from files
    T1_wm_data = T1_wm.get_fdata()
    T1_gm_data = T1_gm.get_fdata()
    T1_csf_data = T1_csf.get_fdata()
    Ktrans_wm_data = Ktrans_wm.get_fdata()
    Ktrans_gm_data = Ktrans_gm.get_fdata()
    Ktrans_csf_data = Ktrans_csf.get_fdata()
    
    mri_shape = T1_wm_data.shape
    slice_num = min(mri_shape[0], mri_shape[1], mri_shape[2])

    T1_wm_mean = []
    T1_gm_mean = []
    T1_csf_mean = []
    Ktrans_wm_mean = []
    Ktrans_gm_mean = []
    Ktrans_csf_mean = []

    # get mean of each matter slice
    for i in range(slice_num):
        a = np.where(T1_wm_data[:, :, i] > 0)
        T1_wm_mean.append(T1_wm_data[:, :, i][a].mean())
        a = np.where(T1_gm_data[:, :, i] > 0)
        T1_gm_mean.append(T1_gm_data[:, :, i][a].mean())
        a = np.where(T1_csf_data[:, :, i] > 0)
        T1_csf_mean.append(T1_csf_data[:, :, i][a].mean())
        
        a = np.where(Ktrans_wm_data[:, :, i] > 0)
        Ktrans_wm_mean.append(Ktrans_wm_data[:, :, i][a].mean())
        a = np.where(Ktrans_gm_data[:, :, i] > 0)
        Ktrans_gm_mean.append(Ktrans_gm_data[:, :, i][a].mean())
        a = np.where(Ktrans_csf_data[:, :, i] > 0)
        Ktrans_csf_mean.append(Ktrans_csf_data[:, :, i][a].mean())

    # Figure city
    n_bins = 500
    fig, ((ax0, ax1), (ax2, ax3)) = plt.subplots(2, 2, figsize=(20,6))
    
    T1_wm_data = np.reshape(T1_wm_data, (320*320*14))
    T1_gm_data = np.reshape(T1_gm_data, (320*320*14))
    T1_csf_data = np.reshape(T1_csf_data, (320*320*14))
    
    Ktrans_wm_data = np.reshape(Ktrans_wm_data, (320*320*14))
    Ktrans_gm_data = np.reshape(Ktrans_gm_data, (320*320*14))
    Ktrans_csf_data = np.reshape(Ktrans_csf_data, (320*320*14))

    ax0.set_xlabel('T1')
    ax0.set_ylabel('Frequency')
    ax0.hist(T1_wm_data[T1_wm_data > 10], n_bins, range=(0, 4000), histtype='bar', color = 'pink', label = "wm")
    ax0.hist(T1_gm_data[T1_gm_data > 10], n_bins, range=(0, 4000),histtype='bar', color = 'gray', label = 'gm')
    ax0.hist(T1_csf_data[T1_csf_data > 10], n_bins, range=(0, 4000), histtype='bar', color = 'cyan', label = 'csf')
    ax0.legend()
    
    ax1.set_xlabel('Ktrans')
    ax1.set_ylabel('Frequency')
    ax1.hist(Ktrans_gm_data[Ktrans_gm_data > 0], n_bins, range=(0.000001, .02), histtype='bar', alpha=1, color = 'gray', label = 'gm')
    ax1.hist(Ktrans_wm_data[Ktrans_wm_data > 0], n_bins, range=(0.000001, .02), histtype='bar', alpha=0.7, color = 'pink', label = 'wm')
    ax1.hist(Ktrans_csf_data[Ktrans_csf_data > 0], n_bins, range=(0.000001, .02), histtype='bar', alpha=0.4, color = 'cyan', label = 'csf')
    ax1.legend()
    
    ax2.set_xlabel('Slice #')
    ax2.set_ylabel('T1 Matter Means')
    ax2.plot(range(slice_num), T1_wm_mean, label = 'wm', color = 'pink')
    ax2.plot(range(slice_num), T1_gm_mean, label = 'gm', color = 'gray')
    ax2.plot(range(slice_num), T1_csf_mean, label = 'csf', color = 'cyan')
    ax2.legend()
    
    ax3.set_xlabel('Slice #')
    ax3.set_ylabel('Ktrans Matter Means')
    ax3.plot(range(slice_num), Ktrans_wm_mean, label = 'wm', color = 'pink')
    ax3.plot(range(slice_num), Ktrans_gm_mean, label = 'gm', color = 'gray')
    ax3.plot(range(slice_num), Ktrans_csf_mean, label = 'csf', color = 'cyan')
    ax3.legend()

    # Save graphs
    path2 = file_dir + '/T1_Ktrans_analysis.png'
    plt.savefig(path2)
    print(file_dir)


dir = Path(sys.argv[1])     # takes timepoint directory as argument
analyze(str(dir))
