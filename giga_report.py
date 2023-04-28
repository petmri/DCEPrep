import datetime
import sys
import jinja2
import json
import nibabel as nib
import numpy as np
import subprocess
from nilearn import plotting
import matplotlib.pyplot as plt

dir = sys.argv[1]
files_to_reorient = [dir + '/2.nii', dir + '/dce_patlak_fit_Ktrans.nii']
for file in files_to_reorient:

    command = ['c3d', file, '-orient', 'RAS', '-o', file[:-4] + '_RAS.nii']
    subprocess.run(command, check=True)

ktrans = nib.load(str(dir) + '/dce_patlak_fit_Ktrans_RAS.nii')
ktrans_data = ktrans.get_fdata()
ktrans_flipped = np.flip(ktrans_data, axis=1)
ktrans_flipped = nib.Nifti1Image(ktrans_flipped, ktrans.affine, ktrans.header)


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

data = {
    'title': subject_id + ' Report',
    'heading': 'Summary',
    'Subject': 'Subject ID: ' + subject_id,
    'Date': 'Date: ' + date,
    'Commit': 'Commit: ' + commit_hash,
    'Institute': 'Institute: ' + institute,
    'Machine': 'Machine: ' + manufacturer + ' ' + dce['ManufacturersModelName'] + ' ' + str(dce['MagneticFieldStrength']) + 'T',
    'ktrans': dir + '/ktrans.svg',
    'image_path1': '/media/network_mriphysics/USC-PPG/data/1101743/skip/dceAIF_fitting.png',
    'image_alt1': 'My image',
    'image_path2': '/media/network_mriphysics/USC-PPG/data/1101743/skip/dce_timecurves.png',
    'image_alt2': 'My image2',
    'Dimensions': 'Dimensions: ' + str(dimensions),
    'Voxel_Size': 'Voxel Size: ' + str(voxel_size),
    'T1w_Segmentation': '',
}

output = template.render(data)

# write html to file
with open('output.html', 'w') as f:
    f.write(output)