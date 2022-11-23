import json
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.gridspec as gridspec
from matplotlib.axes import _secondary_axes
from matplotlib.animation import adjusted_figsize
from matplotlib.pyplot import subplots_adjust
from mpl_toolkits.axes_grid1 import ImageGrid
import numpy as np
import nibabel as nib
from pathlib import Path
import sys


dir = Path(sys.argv[1])
try:
    cmap = str(Path(sys.argv[2]))
except:
    cmap = 'gnuplot'


analysis = mpimg.imread(str(dir) + '/T1_Ktrans_analysis.png')
zeros = mpimg.imread(str(dir) + '/T1_Ktrans_zeros.png')
aif_curve = mpimg.imread(str(dir) + '/dceAIF_fitting.png')
timecurves = mpimg.imread(str(dir) + '/dce_timecurves.png')
plots = []
plots.append(mpimg.imread(str(dir) + '/T1_Ktrans_zeros.png'))
plots.append(mpimg.imread(str(dir) + '/displacements.png'))
curves = []
curves.append(mpimg.imread(str(dir) + '/dceAIF_fitting.png'))
curves.append(mpimg.imread(str(dir) + '/dce_timecurves.png'))
ktrans = nib.load(str(dir) + '/dce_patlak_fit_Ktrans.nii')
try:
    json_file = open(str(dir) + '/DCE.json')
    json_dict = json.load(json_file)
    site = json_dict['InstitutionName']
except:
    site = "no json"

dim = {0,1,2}
ktrans_data = ktrans.get_fdata()
ktrans_shape = ktrans_data.shape
slice_num = min(ktrans_shape[0], ktrans_shape[1], ktrans_shape[2])
slice_loc = ktrans_shape.index(slice_num)
ktrans_data = np.reshape(ktrans_data, (ktrans_shape[min(dim-set([slice_loc]))], ktrans_shape[max(dim-set([slice_loc]))], slice_num))
slices = []
for i in range(slice_num):
    slices.append(ktrans_data[:,:,i].T)

fig, axs = plt.subplots(4, 1, figsize=(8.5,11))
subject = str(dir).split('/')[5]
axs[0].set_title(subject + ' (' + site + ')', y=1.02)
plt.suptitle(str(dir), fontsize='small', y=1)
axs[0].axis('off')
axs[0].imshow(analysis)
axs[1].axis('off')
x = axs[1].imshow(zeros, cmap='gnuplot', vmin=0, vmax=.009)
axs[2].axis('off')
axs[3].axis('off')

gspec = axs[1].get_subplotspec().get_gridspec()
gridspec = axs[2].get_subplotspec().get_gridspec()
gridspec2 = axs[3].get_subplotspec().get_gridspec()
sf = fig.add_subfigure(gspec[1,:])
subfig = fig.add_subfigure(gridspec[2,:])
subfig2 = fig.add_subfigure(gridspec2[3,:])
plot_rows = sf.subplots(1,2)
if slice_num > 8:
    row = subfig.subplots(2,int(slice_num/2))
else:
    row = subfig.subplots(1,slice_num)
curve_rows = subfig2.subplots(1,2)

# cmap = 'gnuplot'
i = 0
for ax in plot_rows:
    ax.axis('off')
    ax.imshow(plots[i])
    i += 1

i = 0
for ax in row.flat:
    ax.axis('off')
    ax.set_xlim(30, 290)
    ax.set_ylim(20, 310)
    # ax.pcolormesh(slices[i], cmap=cmap, vmin=0, vmax=.009)
    x=ax.imshow(slices[i], cmap=cmap, vmin=0, vmax=0.009)
    i+=1

i = 0
for ax in curve_rows:
    ax.axis('off')
    ax.imshow(curves[i])
    i+=1

# fig.tight_layout(pad=-.7)
subplots_adjust(top=0.99, bottom=0.0, left=-0.0, right=1.0, hspace=0, wspace=-.0)
# cax = fig.add_axes([0.0, 0.23, 1, .02])
# bozo = fig.colorbar(x, orientation='horizontal', label='Ktrans (/min)', pad=.02, aspect = 60)
cax = fig.add_axes([1,0.251,.01,.246])
bozo = fig.colorbar(x, cax=cax, orientation='vertical', label='Ktrans (/min)', pad=.02)
bozo.set_label('Ktrans (10^-3/min)', labelpad=-15, fontsize = 'xx-small', color = 'white')
bozo.ax.set_yticklabels(range(0,10), fontsize = 'xx-small')

plt.savefig(str(dir) + '/report.png', bbox_inches='tight')

## REGISTRATION QC
diff = nib.load(str(dir) + '/bozo.nii.gz')
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

plt.savefig(str(dir) + '/wm_reg_QC.png', bbox_inches='tight')
