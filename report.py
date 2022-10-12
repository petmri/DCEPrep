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
from nibabel import orientations


dir = Path(sys.argv[1])
try:
    cmap = str(Path(sys.argv[2]))
except:
    cmap = 'gnuplot'


analysis = mpimg.imread(str(dir) + '/T1_Ktrans_analysis.png')
zeros = mpimg.imread(str(dir) + '/T1_Ktrans_zeros.png')
aif_curve = mpimg.imread(str(dir) + '/dceAIF_fitting.png')
timecurves = mpimg.imread(str(dir) + '/dce_timecurves.png')
curves = []
curves.append(mpimg.imread(str(dir) + '/dceAIF_fitting.png'))
curves.append(mpimg.imread(str(dir) + '/dce_timecurves.png'))
ktrans = nib.load(str(dir) + '/dce_patlak_fit_Ktrans.nii')

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
axs[0].set_title(subject, y=1.02) #+ " (" + str(dir) + "")
plt.suptitle(str(dir), fontsize='small', y=1)
axs[0].axis('off')
axs[0].imshow(analysis)
axs[1].axis('off')
x = axs[1].imshow(zeros, cmap='gnuplot', vmin=0, vmax=.009)
axs[2].axis('off')
axs[3].axis('off')

gridspec = axs[2].get_subplotspec().get_gridspec()
gridspec2 = axs[3].get_subplotspec().get_gridspec()
subfig = fig.add_subfigure(gridspec[2,:])
subfig2 = fig.add_subfigure(gridspec[3,:])
row = subfig.subplots(2,int(slice_num/2))
curve_rows = subfig2.subplots(1,2)

# cmap = 'gnuplot'
i = 0
for ax in row.flat:
    ax.axis('off')
    ax.set_xlim(30, 290)
    ax.set_ylim(20, 310)
    # ax.pcolormesh(slices[i], cmap=cmap, vmin=0, vmax=.009)
    ax.imshow(slices[i], cmap=cmap, vmin=0, vmax=0.009)
    i+=1

i = 0
for ax in curve_rows:
    ax.axis('off')
    ax.imshow(curves[i])
    i+=1

# fig.tight_layout(pad=-.7)
subplots_adjust(top=0.99, bottom=0.0, left=-0.0, right=1.0, hspace=0, wspace=-.0)
# cax = fig.add_axes([0.0, 0.23, 1, .02])
bozo = fig.colorbar(x, orientation='horizontal', label='Ktrans (/min)', pad=.02, aspect = 60)
bozo.set_label('Ktrans (/min)', labelpad=-34.5, fontsize = 'x-small')

# plt.show()
plt.savefig(str(dir) + '/report.png', bbox_inches='tight')
