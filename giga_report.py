import datetime
import sys
import jinja2
import json
import nibabel as nib
import numpy as np
import subprocess
from nilearn import plotting
import matplotlib.pyplot as plt
import re

dir = sys.argv[1]
files_to_reorient = [dir + '/2.nii', dir + '/dce_patlak_fit_Ktrans.nii', dir + '/T1_wm_mask.nii.gz', dir + '/t1_map_fixed_use_me.nii.gz', dir + '/T1_bet_mask_dyn.nii.gz', dir + '/T1_wm_mask_dyn.nii.gz', dir + '/T1_gm_mask_dyn.nii.gz']
for file in files_to_reorient:
    file_no_extension = file.split('.')[0]
    command = ['c3d', file, '-orient', 'RAS', '-o', file_no_extension + '_RAS.nii']
    subprocess.run(command, check=True)

ktrans = nib.load(str(dir) + '/dce_patlak_fit_Ktrans_RAS.nii')
ktrans_data = ktrans.get_fdata()
ktrans_flipped = np.flip(ktrans_data, axis=1)
ktrans_flipped = nib.Nifti1Image(ktrans_flipped, ktrans.affine, ktrans.header)


# save plot of Ktrans
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(15, 5), gridspec_kw={'hspace': -.1, 'wspace': -.1}, dpi=300)
expected_ktrans_vmax = 0.005
plotting.plot_anat(ktrans_flipped, display_mode='z', cut_coords=range(-124, -159, -5), axes=axes[0], vmin=0, vmax=expected_ktrans_vmax, cmap='gnuplot', annotate=False, colorbar=True)
plotting.plot_anat(ktrans_flipped, display_mode='z', cut_coords=range(-159, -194, -5), axes=axes[1], vmin=0, vmax=expected_ktrans_vmax, cmap='gnuplot', annotate=False)
plt.savefig(str(dir) + '/ktrans.svg', bbox_inches='tight', pad_inches = 0)


# use jinja2 to generate html
env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
template = env.get_template('template.html')

# get date
date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# get commit hash
commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()

# get subject id
subject_id = dir.split('/')[-2]
# get institute from DCE.json
with open(str(dir) + '/DCE.json') as f:
    dce = json.load(f)
institute = dce['InstitutionName']
manufacturer = dce['Manufacturer']
dimensions = ktrans.header.get_data_shape()
voxel_size = ktrans.header.get_zooms()

# brain mask
plotting.plot_roi(str(dir) + '/T1_bet_mask.nii.gz', bg_img=str(dir)+'/T1.nii', vmin=0, vmax=1, cmap='gray', output_file=str(dir)+'/t1w_mask.svg', annotate=False, colorbar=False, draw_cross=False, title='mask')

# T1w segmentation
plotting.plot_anat(str(dir) + '/T1.nii', cmap='gray', output_file=str(dir)+'/t1w.svg', annotate=False, colorbar=False, draw_cross=False)
plotting.plot_roi(str(dir) + '/segmented_t1_seg_2.nii.gz', bg_img=str(dir)+'/T1.nii', vmin=0, vmax=1, cmap='gray', output_file=str(dir)+'/t1w_wm.svg', annotate=False, colorbar=False, draw_cross=False, title='wm')
plotting.plot_roi(str(dir) + '/segmented_t1_seg_1.nii.gz', bg_img=str(dir)+'/T1.nii', vmin=0, vmax=1, cmap='gray', output_file=str(dir)+'/t1w_gm.svg', annotate=False, colorbar=False, draw_cross=False, title='gm')

# T1w to VFA
plotting.plot_anat(str(dir) + '/T1_wm_mask_RAS.nii', cmap='gray', output_file=str(dir)+'/t1w_to_vfa.svg', cut_coords=7, display_mode='z', annotate=False, colorbar=False, draw_cross=False, title='T1w to VFA')

# T1w to dyn
plotting.plot_anat(str(dir) + '/T1_bet_mask_dyn_RAS.nii', cmap='gray', output_file=str(dir)+'/t1bet_to_dyn.svg', cut_coords=7, display_mode='z', annotate=False, colorbar=False, draw_cross=False, title='T1w brain mask to dyn')
plotting.plot_anat(str(dir) + '/T1_wm_mask_dyn_RAS.nii', cmap='gray', output_file=str(dir)+'/t1wm_to_dyn.svg', cut_coords=7, display_mode='z', annotate=False, colorbar=False, draw_cross=False, title='T1w wm to dyn')
plotting.plot_anat(str(dir) + '/T1_gm_mask_dyn_RAS.nii', cmap='gray', output_file=str(dir)+'/t1gm_to_dyn.svg', cut_coords=7, display_mode='z', annotate=False, colorbar=False, draw_cross=False, title='T1w gm to dyn')

# T1 map
# read txt file
FAs = []
is_target_line = False
with open(str(dir) + '/T1_map_t1_fa_fit_VFA_mc.txt', 'r') as f:
    for line in f:
        if "User selected TE/TR/FA/TI: " in line:
            is_target_line = True
        elif is_target_line:
            match = re.search(r'\d+', line)
            if match:
                number = int(match.group())
                FAs.append(number)
            else:
                is_target_line = False
# take last set of non-repeating numbers
FAs = FAs[-5:]
# convert from list to string
FA_str = [str(i) for i in FAs]
FA_str = ', '.join(FA_str)

# now get TR from txt file
TR = None
is_target_line = False
with open(str(dir) + '/T1_map_t1_fa_fit_VFA_mc.txt', 'r') as f:
    for line in f:
        if "User selected tr: " in line:
            is_target_line = True
        elif is_target_line:
            match = re.search(r'\d+.\d+', line)
            if match:
                TR = match.group()
            else:
                is_target_line = False

# check if GPU was used
GPU = False
with open(str(dir) + '/T1_map_t1_fa_fit_VFA_mc.txt', 'r') as f:
    for line in f:
        if "GPU detected" in line:
            GPU = True
if GPU:
    GPU_T1 = 'GPU was used'
else:
    GPU_T1 = 'CPU was used'

# T1 map
plotting.plot_anat(str(dir) + '/t1_map_fixed_use_me.nii.gz', cmap='gray', output_file=str(dir)+'/t1_map.svg', annotate=False, colorbar=False, draw_cross=False, title='T1 map')

# AIF
plotting.plot_roi(str(dir) + '/aif.nii', bg_img=str(dir)+'/15.nii', vmin=0, vmax=1, cmap='gray', output_file=str(dir)+'/AIF.svg', annotate=False, colorbar=False, draw_cross=False, title='AIF')

# T1 dynamic space

# get DCE parameters
import re

def extract_value(pattern, text):
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

with open(dir + '/A_dceR1info.log', 'r') as file:
    log_text = file.read()

tr_pattern = r"User selected TR \(ms\):\s+(\d+\.\d+)"
fa_pattern = r"User selected FA \(degrees\):\s+(\d+)"
hematocrit_pattern = r"User selected hematocit \(0 to 1.0\):\s+(\d+\.\d+)"
snr_threshold_pattern = r"User selected SNR threshold for AIF:\s+(\d+)"
relaxivity_pattern = r"User selected contrast agent R1 relaxivity \(/mM/sec\):\s+(\d+\.\d+)"
steady_state_pattern = r"User selected end of steady state time \(image number\):\s+(-?\d+)"

tr = extract_value(tr_pattern, log_text)
fa = extract_value(fa_pattern, log_text)
hematocrit = extract_value(hematocrit_pattern, log_text)
snr_threshold = extract_value(snr_threshold_pattern, log_text)
relaxivity = extract_value(relaxivity_pattern, log_text)
steady_state = extract_value(steady_state_pattern, log_text)

# get last line of log file
with open(dir + '/A_dceR1info.log', 'r') as file:
    for line in file:
        pass
    A_last_line = line

# now get Time Resolution from log file
time_resolution = None
is_target_line = False
with open(str(dir) + '/B_dcefitted_R1info.log', 'r') as f:
    for line in f:
        if "User selected time resolution (sec)" in line:
            is_target_line = True
        elif is_target_line:
            match = re.search(r'(\d+)(.*)\d*', line)
            if match:
                time_resolution = match.group()
            else:
                is_target_line = False

# now get R^2 from log file
r_squared = None
is_target_line = False
with open(str(dir) + '/B_dcefitted_R1info.log', 'r') as f:
    for line in f:
        if "User selected time resolution (sec)" in line:
            is_target_line = True
        elif is_target_line:
            match = re.search(r'(\d+)(.*)\d*', line)
            if match:
                r_squared = match.group()
            else:
                is_target_line = False

def extract_r2_values(log_text):
    r2_pattern = r"R\^2 of AIF fit = (\d+\.\d+)"
    r2_values = re.findall(r2_pattern, log_text)
    return r2_values

with open(dir + '/B_dcefitted_R1info.log', 'r') as file:
    log_text = file.read()

r2_values = extract_r2_values(log_text)

if len(r2_values) >= 2:
    r2_aif_fit = r2_values[-2]
    r2_raw_values = r2_values[-1]

# get last line of B log file (time elapsed)
with open(dir + '/B_dcefitted_R1info.log', 'r') as file:
    for line in file:
        pass
    B_last_line = line

# get GPU info
GPU = False
with open(str(dir) + '/dce_patlak_fit.log', 'r') as f:
    for line in f:
        if "Gpufit detected" in line:
            GPU = True
if GPU:
    GPU_DCE = 'GPU was used'
else:
    GPU_DCE = 'CPU was used'

# get RUN D time elapsed
def extract_elapsed_time(log_text):
    elapsed_time_pattern = r"Elapsed time is (\d+\.\d+) seconds."
    match = re.search(elapsed_time_pattern, log_text)
    if match:
        return match.group(1)
    return None

with open(dir + '/dce_patlak_fit.log', 'r') as file:
    log_text = file.read()

dce_elapsed_time = extract_elapsed_time(log_text)

# Ktrans

data = {
    'title': subject_id + ' Report',
    'heading': 'Summary',
    'Subject': 'Subject ID: ' + subject_id,
    'Date': 'Date: ' + date,
    'Commit': 'Commit: ' + commit_hash,
    'Institute': 'Institute: ' + institute,
    'Machine': 'Machine: ' + manufacturer + ' ' + dce['ManufacturersModelName'] + ' ' + str(dce['MagneticFieldStrength']) + 'T',
    'ktrans': dir + '/ktrans.svg',
    'image_path1': dir + '/dceAIF_fitting.png',
    'image_alt1': 'My image',
    'image_path2': dir + '/dce_timecurves.png',
    'image_alt2': 'My image2',
    'Dimensions': 'Dimensions: ' + str(dimensions),
    'Voxel_Size': 'Voxel Size: ' + str(voxel_size),
    'Overlay': dir + '/overlay.svg',
    'T1w': dir + '/t1w.svg',
    'T1w_mask': dir + '/t1w_mask.svg',
    'T1w_gm': dir + '/t1w_gm.svg',
    'T1w_wm': dir + '/t1w_wm.svg',
    'T1w_to_VFA': dir + '/t1w_to_vfa.svg',
    'FA_1' : 'FA ' + str(FAs[0]),
    'FA_2' : 'FA ' + str(FAs[1]),
    'FA_3' : 'FA ' + str(FAs[2]),
    'FA_4' : 'FA ' + str(FAs[3]),
    'FA_5' : 'FA ' + str(FAs[4]),
    'Z_1' : dir + '/2_BFC_Z.svg',
    'Z_2' : dir + '/5_BFC_Z.svg',
    'Z_3' : dir + '/10_BFC_Z.svg',
    'Z_4' : dir + '/12_BFC_Z.svg',
    'Z_5' : dir + '/15_BFC_Z.svg',
    'T1_TR': 'TR: ' + str(TR) + 'ms',
    'T1_FAs': 'FAs: ' + FA_str,
    'T1_GPU': str(GPU_T1),
    'T1_map': dir + '/t1_map.svg',
    'AIF_mask': dir + '/AIF_mask.svg',
    'AIF_curve': dir + '/AIF_curve.svg',
    't1w_bet_dyn' : dir + '/t1bet_to_dyn.svg',
    't1w_wm_dyn' : dir + '/t1wm_to_dyn.svg',
    't1w_gm_dyn' : dir + '/t1gm_to_dyn.svg',
    'Z_DCE' : dir + '/DCE_mc_bfc_norm.png',
    'TR' : 'Repetition Time: ' + str(tr) + 's',
    'FA' : 'Flip Angle: ' + str(fa) + '°',
    'Hematocrit' : 'Hematocrit: ' + str(hematocrit),
    'SNR_Threshold' : 'SNR Threshold: ' + str(snr_threshold),
    'Relaxivity' : 'Relaxivity: ' + str(relaxivity) + '/mM/sec',
    'A_last_line' : str(A_last_line),
    'Time_Resolution' : 'Time Resolution: ' + str(time_resolution) + 's',
    'R_squared_fit' : 'R squared of AIF fit (fitted): ' + str(r2_aif_fit),
    'R_squared_raw' : 'R squared of AIF fit (raw): ' + str(r2_raw_values),
    'B_last_line' : str(B_last_line),
    'DCE_AIF_fit' : dir + '/dceAIF_fitting.png',
    'DCE_AIF_timecurve' : dir + '/dce_timecurves.png',
    'DCE_model' : 'Model: Patlak',
    'GPU_DCE' : str(GPU_DCE),
    'DCE_elapsed_time' : 'Elapsed time: ' + str(dce_elapsed_time) + 's',
    'ktrans_zeros' : dir + '/T1_Ktrans_zeros.png',
    'ktrans_analysis' : dir + '/T1_Ktrans_analysis.png',
}

output = template.render(data)

# write html to file
with open('output.html', 'w') as f:
    f.write(output)