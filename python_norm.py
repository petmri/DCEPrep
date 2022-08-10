'''
PYTHON PROGRAM FROR Z-AXIS NORMALIZATION

PLEASE FOLLOW THE STEPS BELOW SO THAT THE CODE WORKS PROPERLY - 
IN THE HOME DIRECTORY -
STEP 1: DOWNLOAD AND INSTALL python 3
STEP 2: DOWNLOAD AND INSTALL pip
STEP 3: RUN THE FOLLOWING COMMANDS ON TERMINAL - 
	pip install numpy
	pip install nibabel
	pip install matplotlib
	pip install scipy
SETP 4: RUN THE PYTHON CODE (AFTER PLACING IT IN THE CORRECT LOCATION ON THE COMPUTER, GIVEN BELOW IN THE DIAGRAM) WITH THE COMMAND - python3 python_norm.py

ALSO, IT IS ESSENTIAL THAT THE INPUT DATA AND THIS CODE IS PLACED IN THE PROPER DIRECTORY/FOLDER, SO THAT IT CAN SEARCH AND PROCESS FILES OF ALL SUBJECTS. THE OUTPUT FILES ARE GENERATED AT THE SAME LOCATION OF THE INPUT FILES (FOR EACH SUBJECT).

THE DIRECTORY STRUCTURE TO BE MAINTAINED - 

  directory
	|
	|
	|
	sub directory 1 (containing each subjects' folder and this file)
								|
								|
								|
								--- subject folder
								|	|
								|	|
								|	|---- folder named "1st_timepoint"
								|	|			|
								|	|			|
								|	|			|
								|	|			---- file named "2_new.nii.gz"
								|	|			|
								|	|			---- file named "5_new.nii.gz"
								|	|			|
								|	|			---- file named "10_new.nii.gz"
								|	|			|
								|	|			---- file named "12_new.nii.gz"
								|	|			|
								|	|			---- file named "15_new.nii.gz"
								|	|
								|	|
								|	|
								|	|---- folder named "2nd_timepoint"
								|				|
								|				|
								|				|
								|				---- file named "2_new.nii.gz"
								|				|
								|				---- file named "5_new.nii.gz"
								|				|
								|				---- file named "10_new.nii.gz"
								|				|
								|				---- file named "12_new.nii.gz"
								|				|
								|				---- file named "15_new.nii.gz"
								|	
								|
								|
								|
								--- this file

'''
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

def normalize(mri_file1, file_dir):			# THE FUNCTION PERFORMING THE NORMALIZATION
    img1 = nib.load(mri_file1)
    num = int(re.search(r'\d+', mri_file1.split('/')[-1]).group())
    img_data1 = img1.get_fdata()
    data = []
    for i in range(14):
    	a = np.where(img_data1[:, :, i] > 0)
    	data.append(img_data1[:,:,i][a].mean())
    data_mean = mean(data[1:13])
    std_dev = pstdev(data[1:13])
    err = 1*std_dev
    slice_index = []
    min_val = data_mean - err
    max_val = data_mean + err
    for i in range (14):
        if not (min_val <= data[i] <= max_val):
            slice_index.append(i)
    img_data2 = img_data1

    for i in slice_index:				    
        norm_val1 = img_data1[:, :, i] * (data_mean/data[i])
        img_data2[:, :, i] = norm_val1

    data1 = []
    for i in range(14):
    	a = np.where(img_data2[:, :, i] > 0)
    	data1.append(img_data2[:,:,i][a].mean())
    data_mean1 = mean(data1)

    fig, (ax1, ax2) = plt.subplots(1, 2, sharex = True, sharey=True, figsize=(20,6))
    ax1.plot(data, 'o-', ms=4)
    ax1.grid()
    ax2.plot(data1, 'o-', ms=4)
    ax2.grid()
    path2 = file_dir + '/' + str(num) +'_Z.png'			#THE STRING IN THE END CONTAINS THE FILE NAME OF THE GRAPHS GENERATED (I HAVE KEPT IT AS 2_Z.png/5_Z.png/10_Z.png/12_Z.png/15_Z.png AS OF NOW). FOR EACH SUBJECT, THIS FILE GENERATED IS STORED AT THE SAME LOCATION AS THE INPUT FILES
    plt.savefig(path2)

    final_img = nib.Nifti1Image(img_data2, img1.affine)
    path3 = file_dir + '/' + str(num) + '_Z.nii'		#THE STRING IN THE END CONTAINS THE FILE NAME OF THE NORMALIZED NIFTI IMAGE GENERATED (I HAVE KEPT IT AS 2_Z.nii/5_Z.nii/10_Z.nii/12_Z.nii/15_Z.nii AS OF NOW). FOR EACH SUBJECT, THIS FILE GENERATED IS STORED AT THE SAME LOCATION AS THE INPUT FILES
    nib.save(final_img, path3)
    
    
dir1 = Path(os.getcwd())			# CODE TO AUTOMATICALLY PERFORM THIS NORMALIZATION ON ALL SUBJECTS' ALL VFAs IN THIS DIRECTORY
files_in_dir1 = dir1.iterdir()
for file in files_in_dir1:
    if (os.path.isdir(str(file))):
        files_in_dir2 = file.iterdir()
        for item in files_in_dir2:
            if ((str(item).split('/')[-1] == '1st_timepoint') or (str(item).split('/')[-1] == '2nd_timepoint')):		#SEARCHES FOR THE FOLDERS WITH THESE SPECIFIC NAMES (ENCLOSED IN STRINGS)
                files_in_dir3 = item.iterdir()
                for b1_imgs in files_in_dir3:
                    if ((str(b1_imgs).split('/')[-1] == '2_new.nii.gz') or (str(b1_imgs).split('/')[-1] == '5_new.nii.gz') or (str(b1_imgs).split('/')[-1] == '10_new.nii.gz') or		 (str(b1_imgs).split('/')[-1] == '12_new.nii.gz') or (str(b1_imgs).split('/')[-1] == '15_new.nii.gz')):			#SEARCHES FOR THE NIFTI FILES WITH THESE SPECIFIC NAMES (ENCLOSED IN STRINGS)
                        normalize(str(b1_imgs), str(item))									#CALLING THE 'normalize()' FUNCTION TO PERFORM THE NORMALIZATION
