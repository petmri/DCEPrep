import json
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.gridspec as gridspec
from matplotlib.pyplot import subplots_adjust
import numpy as np
import nibabel as nib
from pathlib import Path
import sys
import cairosvg
import imageio


dir = Path(sys.argv[1])
# output_dir = Path(sys.argv[2])
prefix = sys.argv[2]
# try:
#     cmap = str(Path(sys.argv[2]))
# except:
#     cmap = 'gnuplot'


# AIF_overlay = mpimg.imread('figures/AIF_overlay.svg')
curves = []
svg_path = f'figures/{prefix}_desc-AIF_overlay.svg'
png_bytes = cairosvg.svg2png(file_obj=open(svg_path, "rb"))
png_np_array = imageio.imread(png_bytes, format='png')
curves.append(png_np_array)
svg_path = f'figures/{prefix}_desc-AIF_curve.svg'
png_bytes = cairosvg.svg2png(file_obj=open(svg_path, "rb"))
png_np_array = imageio.imread(png_bytes, format='png')
curves.append(png_np_array)
curves.append(mpimg.imread('figures/dceAIF_fitting.png'))
curves.append(mpimg.imread('figures/dce_timecurves.png'))
ktrans = nib.load('dce/' + prefix + '_Ktrans.nii')
analysis = mpimg.imread('figures/' + prefix + '_desc-analysis.png')
zeros = mpimg.imread('figures/' + prefix + '_desc-zeros.png')
aif_curve = mpimg.imread('figures/dceAIF_fitting.png')
timecurves = mpimg.imread('figures/dce_timecurves.png')
plots = []
plots.append(mpimg.imread('figures/' + prefix + '_desc-zeros.png'))
if Path('figures/displacements.png').exists():
    plots.append(mpimg.imread('figures/displacements.png'))
try:
    json_file = open(f'{dir}/dce/{prefix}_DCE.json')
    json_dict = json.load(json_file)
    site = json_dict['InstitutionName']
    date = json_dict['AcquisitionDateTime'].split('T')[0]
    json_file.close()
except:
    site = "no json"
    date = "no json"

dim = {0,1,2}
ktrans_data = ktrans.get_fdata()
ktrans_shape = ktrans_data.shape
slice_num = min(ktrans_shape[0], ktrans_shape[1], ktrans_shape[2])
slice_loc = ktrans_shape.index(slice_num)
ktrans_data = np.reshape(ktrans_data, (ktrans_shape[min(dim-set([slice_loc]))], ktrans_shape[max(dim-set([slice_loc]))], slice_num))
slices = []
for i in range(slice_num):
    slices.append(ktrans_data[:,:,i].T)

fig, axs = plt.subplots(4, 1, figsize=(8.5,11), dpi=300)
subject = str(dir).split('/')[-2]
axs[0].set_title(dir, y=1.02, fontsize='small')
plt.suptitle(str(subject), fontsize='large', y=1.07)  # Increase the y value to add extra space at the top
# put text below the title
axs[0].text(0, 1.2, f'Site: {site}', fontsize='small')
axs[0].text(0, 1.1, f'Scan Date: {date}', fontsize='small')
axs[0].axis('off')
axs[1].axis('off')
axs[2].axis('off')
axs[3].axis('off')
axs[2].imshow(analysis)
x = axs[3].imshow(zeros, cmap='gnuplot', vmin=0, vmax=.009)

gspec = axs[0].get_subplotspec().get_gridspec()
gridspec = axs[1].get_subplotspec().get_gridspec()
gridspec2 = axs[3].get_subplotspec().get_gridspec()
subfig1 = fig.add_subfigure(gspec[3,:])
subfig2 = fig.add_subfigure(gridspec[1,:])
subfig3 = fig.add_subfigure(gridspec2[0,:])
plot_rows = subfig1.subplots(1,2)
if slice_num > 8:
    row = subfig2.subplots(2,int(slice_num/2))
else:
    row = subfig2.subplots(1,slice_num)
curve_rows = subfig3.subplots(1,4)

# cmap = 'gnuplot'
i = 0
for ax in curve_rows:
    ax.axis('off')
    if i > 1:
        ax.imshow(curves[i], aspect='auto')
    else:
        ax.imshow(curves[i])
    i+=1

i = 0
for ax in row.flat:
    ax.axis('off')
    ax.set_xlim(30, 290)
    ax.set_ylim(20, 310)
    # ax.pcolormesh(slices[i], cmap=cmap, vmin=0, vmax=.009)
    x=ax.imshow(slices[i], cmap='gnuplot', vmin=0, vmax=0.009)
    i+=1

i = 0
for ax in plot_rows:
    ax.axis('off')
    ax.imshow(plots[i])
    i += 1

# fig.tight_layout(pad=-.7)
subplots_adjust(top=0.99, bottom=0.0, left=-0.0, right=1.0, hspace=0, wspace=-.0)
# cax = fig.add_axes([0.0, 0.23, 1, .02])
# colorbar = fig.colorbar(x, orientation='horizontal', label='Ktrans (/min)', pad=.02, aspect = 60)
cax = fig.add_axes([1,0.5,.01,.246])
colorbar = fig.colorbar(x, cax=cax, orientation='vertical', label='Ktrans (/min)', pad=.02)
colorbar.set_label('Ktrans (10^-3/min)', labelpad=-15, fontsize = 'xx-small', color = 'white')
colorbar.ax.set_yticklabels(range(0,10), fontsize = 'xx-small')

plt.savefig('reports/' + prefix + '_desc-report.png', bbox_inches='tight')


## REGISTRATION QC
diff = nib.load('anat/' + prefix + '_space-DCEref_label-WMQC.nii.gz')
diff_data = diff.get_fdata()
# diff_shape = diff_data.shape
# diff_data = np.reshape(diff_data, (ktrans_shape[min(dim-set([slice_loc]))], ktrans_shape[max(dim-set([slice_loc]))], slice_num))

fig2, ax2 = plt.subplots(figsize=(20, 6))
ax2.axis('off')
gridspec_reg = ax2.get_subplotspec().get_gridspec()
subfig_reg = fig2.add_subfigure(gridspec_reg[0,:])
if slice_num > 8:
    reg_rows = subfig_reg.subplots(2,int(slice_num/2))
else:
    reg_rows = subfig_reg.subplots(1,slice_num)
i=0
for ax in reg_rows.flat:
    ax.axis('off')
    # ax.set_xlim(30, 290)
    # ax.set_ylim(20, 310)
    # ax.pcolormesh(slices[i], cmap=cmap, vmin=0, vmax=.009)
    x=ax.imshow(diff_data[:,:,i].T, cmap='gray', origin='lower', vmin=0, vmax=500)
    i+=1
fig2.tight_layout(pad=-2)
# ax.imshow(diff_data[:,:,7], cmap=cmap)
# ax.axis('off')

plt.savefig('figures/' + prefix + '_desc-WMQC_DCE.png', bbox_inches='tight')

diff = nib.load('anat/' + prefix + '_space-DCEref_label-GMQC.nii.gz')
diff_data = diff.get_fdata()
# diff_shape = diff_data.shape
# diff_data = np.reshape(diff_data, (ktrans_shape[min(dim-set([slice_loc]))], ktrans_shape[max(dim-set([slice_loc]))], slice_num))

fig3, ax3 = plt.subplots(figsize=(20, 6))
ax3.axis('off')
gridspec_reg = ax3.get_subplotspec().get_gridspec()
subfig_reg = fig3.add_subfigure(gridspec_reg[0,:])
if slice_num > 8:
    reg_rows = subfig_reg.subplots(2,int(slice_num/2))
else:
    reg_rows = subfig_reg.subplots(1,slice_num)
i=0
for ax in reg_rows.flat:
    ax.axis('off')
    # ax.set_xlim(30, 290)
    # ax.set_ylim(20, 310)
    # ax.pcolormesh(slices[i], cmap=cmap, vmin=0, vmax=.009)
    x=ax.imshow(diff_data[:,:,i].T, cmap='gray', origin='lower', vmin=0, vmax=500)
    i+=1
fig3.tight_layout(pad=-2)
# ax.imshow(diff_data[:,:,7], cmap=cmap)
# ax.axis('off')

plt.savefig('figures/' + prefix + '_desc-GMQC_DCE.png', bbox_inches='tight')
