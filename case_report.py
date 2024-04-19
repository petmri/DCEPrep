import datetime
import sys
import jinja2
import json
import nibabel as nib
import numpy as np
import os
import subprocess
import matplotlib.pyplot as plt
import re
from nilearn import plotting
from matplotlib import colors as mcolors

source_dir = sys.argv[1]
# source_dir = sys.argv[2]
prefix = sys.argv[2]
# if source_dir[-1] == '/':
#     source_dir = source_dir[:-1]

files_to_reorient = [f'anat/{prefix}_flip-01_space-DCEref_VFA.nii.gz', f'dce/{prefix}_Ktrans.nii',
                     f'anat/{prefix}_space-DCEref_T1w.nii.gz',
                     f'anat/{prefix}_space-DCEref_label-WM_mask.nii.gz', f'anat/{prefix}_space-DCEref_T1map.nii',
                     f'anat/{prefix}_space-DCEref_desc-brain_mask.nii.gz', f'anat/{prefix}_space-DCEref_label-GM_mask.nii.gz']
# if c3d exists, reorient files to RAS
dimensions = 0
voxel_size = 0
mean_wm = 0
mean_gm = 0
expected_ktrans_vmax = 0.005
if subprocess.run(['which', 'c3d'], stdout=subprocess.PIPE).returncode == 0:
    for file in files_to_reorient:
        file_no_extension = file.split('.')[0]
        command = ['c3d', file, '-orient', 'RAS', '-o', file_no_extension + '_RAS.nii.gz']
        try:
            subprocess.run(command, check=True)
            if file == (f'dce/{prefix}_Ktrans.nii'):
                ktrans = nib.load(f'dce/{prefix}_Ktrans_RAS.nii.gz')
                ktrans_data = ktrans.get_fdata()
                ktrans_flipped = np.flip(ktrans_data, axis=1)
                ktrans_flipped = nib.Nifti1Image(ktrans_flipped, ktrans.affine, ktrans.header)
                dimensions = ktrans.header.get_data_shape()
                voxel_size = ktrans.header.get_zooms()

                # plot ktrans
                fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(15, 5), gridspec_kw={'hspace': -.1, 'wspace': -.1}, dpi=300)
                #read ktrans coordinates
                ktrans_coords = int(ktrans.header['qoffset_z'])
                ktrans_z_slices = min(dimensions)
                midpt = int(ktrans_coords-5*ktrans_z_slices/2)
                max_coord = int(ktrans_coords-5*ktrans_z_slices)
                plotting.plot_anat(ktrans_flipped, display_mode='z', cut_coords=range(ktrans_coords, midpt, -5), axes=axes[0], vmin=0, vmax=expected_ktrans_vmax, cmap='gnuplot', annotate=False, colorbar=True)
                plotting.plot_anat(ktrans_flipped, display_mode='z', cut_coords=range(midpt, max_coord, -5), axes=axes[1], vmin=0, vmax=expected_ktrans_vmax, cmap='gnuplot', annotate=False)
                plt.savefig('figures/ktrans.svg', bbox_inches='tight', pad_inches = 0)
                plt.close()
        except Exception as e:
            print("Error running c3d command: " + ' '.join(command))
            # print("Check if c3d is installed and in your path, or if the target file exists.")
            print(e)
else:
    # use freesurfer's mri_convert to reorient files to RAS
    for file in files_to_reorient:
        file_no_extension = file.split('.')[0]
        command = ['mri_convert', '--in_orientation', 'LPI', file, file_no_extension + '_RAS.nii.gz']
        try:
            subprocess.run(command, check=True)
            if file == (f'dce/{prefix}_Ktrans.nii'):
                ktrans = nib.load(f'dce/{prefix}_Ktrans_RAS.nii.gz')
                ktrans_data = ktrans.get_fdata()
                ktrans_flipped = np.flip(ktrans_data, axis=1)
                ktrans_flipped = nib.Nifti1Image(ktrans_flipped, ktrans.affine, ktrans.header)
                dimensions = ktrans.header.get_data_shape()
                voxel_size = ktrans.header.get_zooms()

                # plot Ktrans, different coords
                fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(15, 5), gridspec_kw={'hspace': -.1, 'wspace': -.1}, dpi=300)
                plotting.plot_anat(ktrans_flipped, display_mode='z', cut_coords=range(-56, -21, 5), axes=axes[0], vmin=0, vmax=expected_ktrans_vmax, cmap='gnuplot', annotate=False, colorbar=True)
                plotting.plot_anat(ktrans_flipped, display_mode='z', cut_coords=range(-21, 13, 5), axes=axes[1], vmin=0, vmax=expected_ktrans_vmax, cmap='gnuplot', annotate=False)
                plt.savefig('figures/ktrans.svg', bbox_inches='tight', pad_inches = 0)
                plt.close()
        except Exception as e:
            print("Error running freesurfer mri_convert (reorient)")
            dimensions = 'ktrans failed to load'
            voxel_size = 'ktrans failed to load'
            print(e)

# use jinja2 to generate html
env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(os.path.realpath(__file__))))
template = env.get_template('template.html')

# get date
date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# get commit hash
try:
    commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=os.path.dirname(os.path.realpath(__file__))).decode('ascii').strip()
except Exception as e:
    print("Git didn't work correctly. Trying a different way of getting latest dev branch commit hash...")
    command = ['cat', '.git/refs/heads/dev']

    commit_hash = subprocess.check_output(command, cwd=os.path.dirname(os.path.realpath(__file__))).decode('ascii').strip()

# get subject id
subject_id = source_dir.split('/')[-2]
timepoint = source_dir.split('/')[-1]
if subject_id.endswith('_timepoint'):
    subject_id = source_dir.split('/')[-3]
    # get timepoint
    timepoint = source_dir.split('/')[-2]

# get institute from DCE.json
try:
    with open(f"{source_dir}dce/{prefix}_DCE.json") as f:
        dce = json.load(f)
    institute = dce['InstitutionName']
    manufacturer = dce['Manufacturer']
    MR_machine_model = dce['ManufacturersModelName']
    field_strength = dce['MagneticFieldStrength']
except Exception as e:
    dce = {}
    institute = 'no json'
    manufacturer = 'no json'
    MR_machine_model = 'no json'
    field_strength = 'no json'
    print("Error loading DCE.json")
    print(e)

try:
    # brain mask
    plotting.plot_roi(f'anat/{prefix}_desc-brain_mask.nii.gz', bg_img=f'{source_dir}/anat/{prefix}_T1w.nii.gz', cut_coords=(-20, 0, -15), vmin=0, vmax=1, dim=-1, cmap='gray', output_file='figures/t1w_mask.svg', colorbar=False, draw_cross=False, title='mask')

    # T1w segmentation
    plotting.plot_anat(f'{source_dir}/anat/{prefix}_T1w.nii.gz', cmap='gray', output_file='figures/t1w.svg', cut_coords=(-20, 0, -15), dim=-1, colorbar=False, draw_cross=False)
    plotting.plot_roi(f'anat/{prefix}_label-WM_mask.nii.gz', bg_img=f'{source_dir}/anat/{prefix}_T1w.nii.gz', cut_coords=(-20, 0, -15), vmin=0, vmax=1, dim=0, cmap='gray', output_file='figures/t1w_wm.svg', colorbar=False, draw_cross=False, title='wm')
    plotting.plot_roi(f'anat/{prefix}_label-GM_mask.nii.gz', bg_img=f'{source_dir}/anat/{prefix}_T1w.nii.gz', cut_coords=(-20, 0, -15), vmin=0, vmax=1, dim=0, cmap='gray', output_file='figures/t1w_gm.svg', colorbar=False, draw_cross=False, title='gm')
except Exception as e:
    print("Error plotting T1w segmentation")
    print(e)

try:
    # T1w to VFA
    # plotting.plot_anat(f'anat/{prefix}_label-WM_mask_RAS.nii.gz', cmap='gray', output_file='figures/t1w_to_dceref.svg', cut_coords=7, display_mode='z', annotate=False, colorbar=False, draw_cross=False, title='T1w to DCEref')

    # T1w to dyn
    t1w_dceref = nib.load(f'anat/{prefix}_space-DCEref_T1w_RAS.nii.gz')
    t1w_dceref_data = t1w_dceref.get_fdata()
    t1w_dceref_flipped = np.flip(t1w_dceref_data, axis=1)
    t1w_dceref_flipped = nib.Nifti1Image(t1w_dceref_flipped, t1w_dceref.affine, t1w_dceref.header)
    plotting.plot_anat(t1w_dceref_flipped, cmap='gray', output_file=f'figures/{prefix}_space-DCEref_T1w.svg', cut_coords=7, display_mode='z', annotate=False, colorbar=False, draw_cross=False, title='T1w to dyn')

    # flip T1w masks
    t1w_mask = nib.load(f'anat/{prefix}_space-DCEref_desc-brain_mask_RAS.nii.gz')
    t1w_mask_data = t1w_mask.get_fdata()
    t1w_mask_flipped = np.flip(t1w_mask_data, axis=1)
    t1w_mask_flipped = nib.Nifti1Image(t1w_mask_flipped, t1w_mask.affine, t1w_mask.header)
    # nib.save(t1w_mask_flipped, str(tp_dir) + '/T1_bet_mask_RAS.nii')

    t1w_wm_mask = nib.load(f'anat/{prefix}_space-DCEref_label-WM_mask_RAS.nii.gz')
    t1w_wm_mask_data = t1w_wm_mask.get_fdata()
    t1w_wm_mask_flipped = np.flip(t1w_wm_mask_data, axis=1)
    t1w_wm_mask_flipped = nib.Nifti1Image(t1w_wm_mask_flipped, t1w_wm_mask.affine, t1w_wm_mask.header)
    # nib.save(t1w_wm_mask_flipped, str(tp_dir) + '/T1_wm_mask_RAS.nii')

    t1w_gm_mask = nib.load(f'anat/{prefix}_space-DCEref_label-GM_mask_RAS.nii.gz')
    t1w_gm_mask_data = t1w_gm_mask.get_fdata()
    t1w_gm_mask_flipped = np.flip(t1w_gm_mask_data, axis=1)
    t1w_gm_mask_flipped = nib.Nifti1Image(t1w_gm_mask_flipped, t1w_gm_mask.affine, t1w_gm_mask.header)
    # nib.save(t1w_gm_mask_flipped, str(tp_dir) + '/T1_gm_mask_RAS.nii')

    plotting.plot_roi(t1w_mask_flipped, cmap='gray', bg_img=t1w_dceref_flipped, output_file='figures/t1bet_to_dyn.svg', display_mode='z', vmin=0, vmax=1, dim=0, annotate=True, colorbar=False, draw_cross=False, title='T1w brain mask to DCEref')
    plotting.plot_roi(t1w_wm_mask_flipped, cmap='gray', bg_img=t1w_dceref_flipped, output_file='figures/t1wm_to_dyn.svg', display_mode='z', vmin=0, vmax=1, dim=0, annotate=True, colorbar=False, draw_cross=False, title='T1w wm to DCEref')
    plotting.plot_roi(t1w_gm_mask_flipped, cmap='gray', bg_img=t1w_dceref_flipped, output_file='figures/t1gm_to_dyn.svg', display_mode='z', vmin=0, vmax=1, dim=0, annotate=True, colorbar=False, draw_cross=False, title='T1w gm to DCEref')
except Exception as e:
    print("Error plotting T1w to dyn")
    print(e)

try:
    # T1 map
    # read txt file
    FAs = []
    is_target_line = False
    with open(f'anat/{prefix}_space-DCEref_T1map.txt', 'r') as f:
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
    with open(f'anat/{prefix}_space-DCEref_T1map.txt', 'r') as f:
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
    with open(f'anat/{prefix}_space-DCEref_T1map.txt', 'r') as f:
        for line in f:
            if "GPU detected" in line:
                GPU = True
    if GPU:
        GPU_T1 = 'GPU was used'
    else:
        GPU_T1 = 'CPU was used'
except Exception as e:
    print("Error getting T1 map parameters")
    FAs = [-1, -1, -1, -1, -1]
    FA_str = 'Failed to load FAs'
    TR = -1
    GPU_T1 = 'Failed to load GPU info'
    print(e)

try:
    # T1 map
    # flip T1 map
    img = nib.load(f'anat/{prefix}_space-DCEref_T1map_RAS.nii.gz')
    img_data = img.get_fdata()
    img_data = np.flip(img_data, axis=0)
    img_data = np.flip(img_data, axis=1)
    t1_map_flipped = nib.Nifti1Image(img_data, img.affine, img.header)
    plotting.plot_anat(t1_map_flipped, cmap='gray', vmin=0, vmax=5000, output_file='figures/t1_map.svg', annotate=False, colorbar=False, draw_cross=False, title='T1 map')
except Exception as e:
    print("Error plotting T1 map")
    print(e)

# try:
# AIF
# plot graph of AIF region
aif = nib.load(f'dce/{prefix}_desc-AIFpos_T1map.nii.gz')
aif_data = aif.get_fdata()
# img = nib.load(str(tp_dir) + '/DCE_mc.nii.gz')
img = nib.load(f'dce/{prefix}_desc-hmc_DCE.nii.gz')
img_data = img.get_fdata()
# binarize AIF
aif_data[aif_data > 0] = 1
aif_data[aif_data < 0] = 0
# mask DCE where AIF is 1
# but first ensure that DCE and AIF have same number of dimensions
if len(aif_data.shape) < len(img_data.shape):
    aif_data = np.expand_dims(aif_data, axis=-1)
aif_data_roi = img_data * aif_data
# sum AIF data for each time point, z-slice independent
aif_curve = np.sum(aif_data_roi, axis=(0, 1, 2)) / np.sum(aif_data[aif_data > 0])
# divide by AIF mean of first timepoint
aif_curve_ratio = aif_curve / aif_curve[0]

# get metric of AIF
def quality_peak(aif_curve):
    peak_ratio = max(aif_curve) / aif_curve[0]
    # peak_ratio = tf.cast(peak_ratio, tf.float32)
    return peak_ratio*(100/7.546971123202499)

def quality_tail(aif_curve):
    # end is mean of last 20% of curve
    end_ratio = np.mean(aif_curve[-int(float(int(len(aif_curve)))*0.2):]) / aif_curve[0]
    # end_ratio = tf.cast(end_ratio, tf.float32)

    quality = (1 / (end_ratio + 1)) * (100/0.24035631585328981)
    # if quality > 200:
    #     quality = 200
    return quality

def quality_peak_to_end(aif_curve):
    peak_ratio = quality_peak(aif_curve)/(100/7.546971123202499)
    end_ratio = np.mean(aif_curve[-int(float(int(len(aif_curve)))*0.2):]) / aif_curve[0]
    # end_ratio = tf.cast(end_ratio, tf.float32)
    
    return (peak_ratio / end_ratio)*(100/2.4085609761976534)

def quality_peak_time(aif_curve):
    peak_time = np.argmax(aif_curve)
    # peak_time = tf.cast(peak_time, tf.float32)
    num_timeslices = len(aif_curve)
    qpt = (num_timeslices - peak_time) / num_timeslices
    return qpt*(100/0.9157142857142857)

def quality_ultimate(aif_curve):
    peak_ratio = quality_peak(aif_curve)
    end_ratio = quality_tail(aif_curve)
    peak_to_end = quality_peak_to_end(aif_curve)
    peak_time = quality_peak_time(aif_curve)

    # take weighted average
    return peak_ratio*0.3 + end_ratio*0.3 + peak_to_end*0.3 + peak_time*0.1
    # return peak_ratio + 0.3*end_ratio + 0.3*peak_to_end + 0.1*peak_time

aif_metric = quality_ultimate(aif_curve_ratio)

# plot AIF
plt.plot(aif_curve_ratio)
plt.text(0.25, 0.95, 'Voxel Baseline Avg SI: ' + str(aif_curve[0]), transform=plt.gca().transAxes, fontsize=11, verticalalignment='top')
plt.text(0.25, 0.9, 'AIFitness: ' + str(aif_metric), transform=plt.gca().transAxes, fontsize=11, verticalalignment='top')
plt.title('AIF Curve')
plt.xlabel('Timepoint')
plt.ylabel('Signal intensity / Baseline')
plt.savefig(f'figures/{prefix}_desc-AIF_curve.svg', bbox_inches='tight')
plt.close()

# save AIF values to file
np.savetxt('dce/AIF_values.txt', aif_curve_ratio)

# plot AIF overlay
plt.figure(figsize=(15,5), dpi=250)
plt.subplot(1,2,1)
plt.axis('off')

# rotate images
img_data = np.rot90(img_data, axes=(0,1))
aif_data = np.rot90(aif_data, axes=(0,1))

# overlay AIF mask
aif_slice = np.where(aif_data > 0)[2][0]
cmap = mcolors.LinearSegmentedColormap.from_list('custom cmap', [(0, 0, 0, 0), 'blue', 'green', 'red'])
plt.imshow(img_data[:,:,aif_slice, 5], cmap='gray')
plt.imshow(aif_data[:,:,aif_slice], cmap=cmap, alpha=1)
plt.savefig(f'figures/{prefix}_desc-AIF_overlay.svg', bbox_inches='tight')
plt.close()
# except Exception as e:
#     print("Error plotting AIF")
#     # print error
#     print(e)

# T1 dynamic space

# get DCE parameters
def extract_value(pattern, text):
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

try:
    with open('dce/A_dceR1info.log', 'r') as file:
        log_text = file.read()
    RUNA_log = True
except Exception as e:
    log_text = ''
    RUNA_log = False
    print("Error getting DCE parameters from A_dceR1info.log")
    print(e)

tr_pattern = r"User selected TR \(ms\):\s+(\d+\.\d+)"
fa_pattern = r"User selected FA \(degrees\):\s+(\d+)"
hematocrit_pattern = r"User selected hematocit \(0 to 1.0\):\s+(\d+\.\d+)"
snr_threshold_pattern = r"User selected SNR threshold for AIF:\s+(\d+)"
relaxivity_pattern = r"User selected contrast agent R1 relaxivity \(/mM/sec\):\s+(\d+\.\d+)"
steady_state_pattern = r"User selected end of steady state time \(image number\):\s+(-?\d+)"

DCE_tr = extract_value(tr_pattern, log_text)
DCE_fa = extract_value(fa_pattern, log_text)
hematocrit = extract_value(hematocrit_pattern, log_text)
snr_threshold = extract_value(snr_threshold_pattern, log_text)
relaxivity = extract_value(relaxivity_pattern, log_text)
steady_state = extract_value(steady_state_pattern, log_text)
blood_t1_pattern = "Average Filtered AIF T1: "

if RUNA_log:
    # get last line of log file
    with open('dce/A_dceR1info.log', 'r') as file:
        match = False
        for line in file:
            if line[:-1] == blood_t1_pattern:
                match = True
            elif match:
                blood_t1 = line[:-1]
                match = False
        A_last_line = line
else:
    A_last_line = 'Failed to load RUNA log'

try:
    # now get Time Resolution from log file
    time_resolution = None
    is_target_line = False
    with open('dce/B_dcefitted_R1info.log', 'r') as f:
        for line in f:
            if "User selected time resolution (sec)" in line:
                is_target_line = True
            elif is_target_line:
                match = re.search(r'(\d+)(.*)\d*', line)
                if match:
                    time_resolution = match.group()
                else:
                    is_target_line = False
    RUNB_log = True
except Exception as e:
    print("Error getting DCE RUNB parameters from B_dcefitted_R1info.log")
    print(e)
    RUNB_log = False

if RUNB_log:
    def extract_r2_values(log_text):
        r2_pattern = r"R\^2 of AIF fit = (-*\d+\.\d+)"
        r2_values = re.findall(r2_pattern, log_text)
        return r2_values

    with open('dce/B_dcefitted_R1info.log', 'r') as file:
        log_text = file.read()

    r2_values = extract_r2_values(log_text)

    if len(r2_values) >= 2:
        r2_aif_fit = r2_values[-2]
        r2_raw_values = r2_values[-1]

    # get last line of B log file (time elapsed)
    with open('dce/B_dcefitted_R1info.log', 'r') as file:
        for line in file:
            pass
        B_last_line = line
else:
    r2_aif_fit = 'Failed to load RUNB log'
    r2_raw_values = 'Failed to load RUNB log'
    B_last_line = 'Failed to load RUNB log'

try:
    # get GPU info
    GPU = False
    with open('dce/dce_patlak_fit.log', 'r') as f:
        for line in f:
            if "Gpufit detected" in line:
                GPU = True
    if GPU:
        GPU_DCE = 'GPU was used'
    else:
        GPU_DCE = 'CPU was used'
    RUND_log = True
except Exception as e:
    print("Error getting DCE GPU info from dce_patlak_fit.log")
    print(e)
    RUND_log = False
    GPU_DCE = 'Failed to load GPU info'

if RUND_log:
    # get RUN D time elapsed
    def extract_elapsed_time(log_text):
        elapsed_time_pattern = r"Elapsed time is (\d+\.\d+) seconds."
        match = re.search(elapsed_time_pattern, log_text)
        if match:
            return match.group(1)
        return None

    with open('dce/dce_patlak_fit.log', 'r') as file:
        log_text = file.read()

    dce_elapsed_time = extract_elapsed_time(log_text)
else:
    dce_elapsed_time = 'Failed to load RUND log'

# Ktrans

# get Ktrans mean wm and gm
KTRANS_MIN_THRESHOLD = 0.00001
ktrans_wm = nib.load(f'dce/{prefix}_seg-WM_Ktrans.nii.gz')
ktrans_wm_data = ktrans_wm.get_fdata()
# mean_wm = np.mean(ktrans_wm_data[ktrans_wm_data > 0])*1000
ktrans_median_wm = np.median(ktrans_wm_data[ktrans_wm_data > KTRANS_MIN_THRESHOLD])*1000
ktrans_std_wm = np.std(ktrans_wm_data[ktrans_wm_data > KTRANS_MIN_THRESHOLD])*1000

ktrans_gm = nib.load(f'dce/{prefix}_seg-GM_Ktrans.nii.gz')
ktrans_gm_data = ktrans_gm.get_fdata()
# mean_gm = np.mean(ktrans_gm_data[ktrans_gm_data > 0])*1000
ktrans_median_gm = np.median(ktrans_gm_data[ktrans_gm_data > KTRANS_MIN_THRESHOLD])*1000
ktrans_std_gm = np.std(ktrans_gm_data[ktrans_gm_data > KTRANS_MIN_THRESHOLD])*1000

# get T1 map median wm and gm
T1_wm = nib.load(f'anat/{prefix}_space-DCEref_label-WM_T1map.nii.gz')
T1_wm_data = T1_wm.get_fdata()
T1_wm_median = np.median(T1_wm_data[T1_wm_data > 0])
T1_wm_std = np.std(T1_wm_data[T1_wm_data > 0])

T1_gm = nib.load(f'anat/{prefix}_space-DCEref_label-GM_T1map.nii.gz')
T1_gm_data = T1_gm.get_fdata()
T1_gm_median = np.median(T1_gm_data[T1_gm_data > 0])
T1_gm_std = np.std(T1_gm_data[T1_gm_data > 0])

# MNI space registration
# fsl_dir = os.environ['FSLDIR']
# print(fsl_dir)
# try:
#     plotting.plot_anat(os.path.dirname(os.path.realpath(__file__)) + '/MNI152_T1_1mm_brain.nii.gz', title='MNI152_T1_1mm_brain', output_file=tp_dir + '/figures/MNI152_T1_1mm_brain.svg', colorbar=False, draw_cross=False)
#     plotting.plot_anat(tp_dir + '/t1w_MNIWarped.nii.gz', title='t1w_MNI', cut_coords=(2, -1, 20), output_file=tp_dir + '/figures/t1w_MNI.svg', colorbar=False, draw_cross=False)
#     plotting.plot_anat(source_dir + '/Ktrans_MNI.nii.gz', title='ktrans_MNI', cut_coords=(2, -1, 20), vmin=0, vmax=0.001, output_file=source_dir + '/figures/Ktrans_MNI.svg', colorbar=False, draw_cross=False)
# except Exception as e:
#     print("Error plotting MNI space registration")
#     print(e)

# if tp_dir != source_dir:
#     tp_figdir = "../"
# else:
#     tp_figdir = ""

data = {
    'title': subject_id + ' ' + timepoint + ' Report',
    'heading': 'Summary',
    'Subject': 'Subject ID: ' + subject_id,
    'Timepoint': 'Timepoint: ' + timepoint,
    'Date': 'Date Processed: ' + date,
    'Commit': 'Commit: ' + commit_hash,
    'Institute': 'Institute: ' + institute,
    'Machine': 'Machine: ' + manufacturer + ' ' + MR_machine_model + ' ' + str(field_strength) + 'T',
    'ktrans': '../figures/ktrans.svg',
    'image_alt1': 'Missing image',
    'Dimensions': 'Dimensions: ' + str(dimensions),
    'Voxel_Size': 'Voxel Size: ' + str(voxel_size),
    'Overlay': '../figures/overlay.svg',
    'T1w': '../figures/t1w.svg',
    'T1w_mask': '../figures/t1w_mask.svg',
    'T1w_gm': '../figures/t1w_gm.svg',
    'T1w_wm': '../figures/t1w_wm.svg',
    'T1w_to_DCEref': '../figures/t1w_to_dceref.svg',
    'T1_TR': 'TR: ' + str(TR) + 'ms',
    'T1_FAs': 'FAs: ' + FA_str,
    'T1_GPU': str(GPU_T1),
    'T1_wm_median': 'T1 wm median: ' + str(round(T1_wm_median, 4)),
    'T1_wm_std': 'T1 wm std: ' + str(round(T1_wm_std, 4)),
    'T1_gm_median': 'T1 gm median: ' + str(round(T1_gm_median, 4)),
    'T1_gm_std': 'T1 gm std: ' + str(round(T1_gm_std, 4)),
    'T1_map': '../figures/t1_map.svg',
    'displacements' : '../figures/displacements.svg',
    'AIF_mask': f'../figures/{prefix}_desc-AIF_mask.svg',
    'AIF_metric' : "AIFitness: " + str(aif_metric),
    'AIF_curve': f'../figures/{prefix}_desc-AIF_resampledcurve.svg',
    'AIF_overlay': f'../figures/{prefix}_desc-AIF_overlay.svg',
    'AIF_graph': f'../figures/{prefix}_desc-AIF_curve.svg',
    't1w_dyn' : f'../figures/{prefix}_space-DCEref_T1w.svg',
    't1w_bet_dyn' : '../figures/t1bet_to_dyn.svg',
    't1w_wm_dyn' : '../figures/t1wm_to_dyn.svg',
    't1w_gm_dyn' : '../figures/t1gm_to_dyn.svg',
    'Z_DCE' : f'../figures/{prefix}_desc-bfcz_DCE.svg',
    'DCE_TR' : 'Repetition Time: ' + str(DCE_tr) + 's',
    'DCE_FA' : 'Flip Angle: ' + str(DCE_fa) + '°',
    'Hematocrit' : 'Hematocrit: ' + str(hematocrit),
    'SNR_Threshold' : 'SNR Threshold: ' + str(snr_threshold),
    'Relaxivity' : 'Relaxivity: ' + str(relaxivity) + '/mM/sec',
    'T1_blood' : 'Blood T1: ' + str(blood_t1) + 's',
    'A_last_line' : str(A_last_line),
    'Time_Resolution' : 'Time Resolution: ' + str(time_resolution) + 's',
    'R_squared_fit' : 'R squared of AIF fit (fitted): ' + str(r2_aif_fit),
    'R_squared_raw' : 'R squared of AIF fit (raw): ' + str(r2_raw_values),
    'B_last_line' : str(B_last_line),
    'DCE_AIF_fit' : '../figures/dceAIF_fitting.png',
    'DCE_AIF_timecurve' : '../figures/dce_timecurves.png',
    'DCE_model' : 'Model: Patlak',
    'GPU_DCE' : str(GPU_DCE),
    'DCE_elapsed_time' : 'Elapsed time: ' + str(dce_elapsed_time) + 's',
    'ktrans_zeros' : f'../figures/{prefix}_desc-zeros.png',
    'ktrans_analysis' : f'../figures/{prefix}_desc-analysis.png',
    'ktrans_wm_mean' : 'Mean wm Ktrans: ' + str(round(mean_wm, 4)),
    'ktrans_wm_median' : 'Median wm Ktrans: ' + str(round(ktrans_median_wm, 4)),
    'ktrans_wm_std' : 'Std wm Ktrans: ' + str(round(ktrans_std_wm, 4)),
    'ktrans_gm_mean' : 'Mean gm Ktrans: ' + str(round(mean_gm, 4)),
    'ktrans_gm_median' : 'Median gm Ktrans: ' + str(round(ktrans_median_gm, 4)),
    'ktrans_gm_std' : 'Std gm Ktrans: ' + str(round(ktrans_std_gm, 4)),
    'MNI_img' : '../figures/MNI152_T1_1mm_brain.svg',
    'MNI_T1w' : '../figures/t1w_MNI.svg',
    'MNI_Ktrans' : '../figures/ktrans_MNI.svg',
}

# insert VFAs into template
flips = ['flip-01', 'flip-02', 'flip-03', 'flip-04', 'flip-05', 'flip-06', 'flip-07']
for i in range(len(FAs)):
    data['FA_' + str(i+1)] = 'FA ' + str(FAs[i])
    data['Z_' + str(i+1)] = f'../figures/{prefix}_{flips[i]}_space-DCEref_desc-bfcz_VFA.svg'

output = template.render(data)

# write html to file
with open(f'reports/{prefix}_desc-casereport.html', 'w') as f:
    f.write(output)

print(f'Report generated in reports/{prefix}_desc-casereport.html')
