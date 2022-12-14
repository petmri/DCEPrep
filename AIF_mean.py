import csv
import nibabel as nib
import numpy as np
import sys
from statistics import mean

# dir = "/media/network_mriphysics/USC-PPG/data/203491_cbf/1st_timepoint"
dir = sys.argv[1]

AIF = nib.load(dir + '/aif.nii')
DCE = nib.load(dir + '/DCE_mc.nii.gz')

AIF_data = AIF.get_fdata()
DCE_data = DCE.get_fdata()

AIF_shape = AIF_data.shape

bozo = DCE_data[np.where(AIF_data>0)[0:3]]

aif_mean = bozo.mean(axis=0)

sec = []
for i in range(len(aif_mean)):
    sec.append(i*15.29)

with open(dir + '/AIF_mean.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["sec", "mean"])
    for i in range(len(aif_mean)):
        writer.writerow([sec[i], aif_mean[i]])
    file.close()