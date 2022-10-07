import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.gridspec as gridspec
from mpl_toolkits.axes_grid1 import ImageGrid
import numpy as np
import nibabel as nib
from matplotlib.axes import _secondary_axes
from matplotlib.animation import adjusted_figsize


img1 = mpimg.imread('/media/network_mriphysics/USC-PPG/data/1101743/1st_timepoint/T1_Ktrans_analysis.png')
img2 = mpimg.imread('/media/network_mriphysics/USC-PPG/data/1101743/1st_timepoint/T1_Ktrans_zeros.png')
img3 = mpimg.imread('/media/network_mriphysics/USC-PPG/data/1101743/1st_timepoint/Ktrans.png')
ktrans = nib.load('/media/network_mriphysics/USC-PPG/data/1101743/1st_timepoint/dce_patlak_fit_Ktrans.nii')

dim = {0,1,2}
ktrans_data = ktrans.get_fdata()
ktrans_shape = ktrans_data.shape
slice_num = min(ktrans_shape[0], ktrans_shape[1], ktrans_shape[2])
slice_loc = ktrans_shape.index(slice_num)
ktrans_data = np.reshape(ktrans_data, (ktrans_shape[min(dim-set([slice_loc]))], ktrans_shape[max(dim-set([slice_loc]))], slice_num))
slices = []
for i in range(slice_num):
    slices.append(ktrans_data[:,:,i].T)
slice0 = ktrans_data[:,:,0].T
# slice0 = np.flipud(slice0)
slice1 = ktrans_data[:,:,1].T
# slice1 = np.flipud(slice1)

# fig = plt.figure(figsize=(20., 20.))
# # fig = plt.figure()
# ax = fig.add_subplot(2, 2, 1)
# plt.axis('off')
# imgplot = plt.imshow(img1)
#
# ax = fig.add_subplot(2, 2, 2)
# plt.axis('off')
# imgplot = plt.imshow(img2)
#
# ax = fig.add_subplot(2, 2, 3)
# ax.pcolormesh(slice0)
# plt.axis('off')
# plt.show()

# fig = plt.figure(figsize=(10, 10))
# grid = ImageGrid(fig, 111,  # similar to subplot(111)
#                  nrows_ncols=(3,1),
#                  axes_pad=0.001,
#                  label_mode="L",
#                  )
#
# # demo image
# for ax, im in zip(grid, [img1, img2, slice0, slice1]):
#     ax.axis('off')
#     ax.imshow(im, origin="upper", cmap='jet', vmin=0, vmax=0.05)

# ax.axis('off')
# ax.imshow(slice0, cmap="jet", vmin=0, vmax=0.05)
# plt.figure(figsize=(7,6))
# plt.colorbar()
# plt.pcolormesh(slice0)

# plt.figure()

# f, ax = plt.subplots(3,1)
# ax[0].imshow(img1)
# ax[0].axis('off')
# ax[1].imshow(img2)
# ax[1].axis('off')
# # ax[2].imshow(slice0, cmap="jet", vmin=0, vmax=0.05)
# # ax[2].axis('off')
# # ax[3].imshow(slice1, cmap="jet", vmin=0, vmax=0.05)
# # ax[3].axis('off')
# plt.subplots_adjust(bottom=0.1)



# gridspec inside gridspec
# fig = plt.figure()

# ax1 = fig.add_subplot(311)
# ax1.imshow(img1)
# ax1.axis('off')
# ax2 = fig.add_subplot(312)
# ax2.imshow(img2)
# ax2.axis('off')
# ax3 = fig.add_subplot(313)
fig, axs = plt.subplots(4, 1)
axs[0].axis('off')
axs[0].imshow(img1)
axs[1].axis('off')
axs[1].imshow(img2)
axs[2].axis('off')

gridspec = axs[2].get_subplotspec().get_gridspec()
gridspec2 = axs[3].get_subplotspec().get_gridspec()
subfig = fig.add_subfigure(gridspec[2,:])
subfig2 = fig.add_subfigure(gridspec[3,:])
axsSlices = subfig.subplots(1,int(slice_num/2))
ax2 = subfig2.subplots(1,int(slice_num/2))

i = 0
cmap = 'plasma'
for ax in axsSlices.flat:
    ax.axis('off')
    ax.pcolormesh(slices[i], cmap=cmap, vmin=0, vmax=.009)
    i+=1

for ax in ax2.flat:
    ax.axis('off')
    ax.pcolormesh(slices[i], cmap=cmap, vmin=0, vmax=.009)
    i+=1
fig.tight_layout(pad=-.7)
# gs01 = gs0[1].subgridspec(nrows, ncols)
# ax2 = fig.add_subplot(gs00[-1, :-1])
# ax3 = fig.add_subplot(gs00[-1, -1])

# the following syntax does the same as the GridSpecFromSubplotSpec call above:
# gs01 = gs0[1].subgridspec(3, 3)
#
# ax4 = fig.add_subplot(gs01[:, :-1])
# ax5 = fig.add_subplot(gs01[:-1, -1])
# ax6 = fig.add_subplot(gs01[-1, -1])
plt.show()
