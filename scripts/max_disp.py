import sys
import matplotlib.pyplot as plt
# import nibabel as nib
import numpy as np
from math import sqrt
# from numpy.lib.function_base import corrcoef
# from sklearn.linear_model import LinearRegression
# from statistics import mean


dir = sys.argv[1]
prefix = sys.argv[2]
mc_params = np.loadtxt(dir + "/" + prefix + "_desc-hmc_DCE.nii.par", dtype=float)
mc_params[:,0:3] = mc_params[:,0:3]*70
max_i = np.abs(mc_params).argmax()
max_disp_i = np.unravel_index(max_i, mc_params.shape)
max_disp = str(mc_params[max_disp_i])
param_num = max_disp_i[1]
# get max displacement of 3d transformation
vector_max_disp = np.zeros(64)
# for i in range(64):
#     vector_max_disp[i] = np.linalg.norm(mc_params[i], axis=0)
# vector_max_disp = np.abs(vector_max_disp).max()
for i in range(len(mc_params[:,0])):
    vector_max_disp = sqrt((mc_params[i,3]+mc_params[i,0])**2 + (mc_params[i,4]+mc_params[i,1])**2 + (mc_params[i,5]+mc_params[i,2])**2)
vector_max_disp = np.abs(vector_max_disp).max()
vector_max_disp_i = np.abs(mc_params).argmax(axis=0)[param_num]+1

if param_num < 4:
    param_type = "rot_"
else:
    param_type = "trans_"
    
if param_num % 3 == 0:
    param_type = param_type + 'x'
elif param_num % 3 == 1:
    param_type = param_type + 'y'
elif param_num % 3 == 2:
    param_type = param_type + 'z'

print("Max displacement: " + str(vector_max_disp) + "mm at frame " + str(vector_max_disp_i) + "/64")

fig, ax = plt.subplots(figsize=(10, 6))
colors = ['k', 'b', 'g', 'm', 'y', 'c']
labels = ['rot_x', 'rot_y', 'rot_z', 'trans_x', 'trans_y', 'trans_z']
for i in range(len(mc_params[0,:])):
    # label = 'param ' + str(i)
    ax.plot(range(len(mc_params[:,i])), mc_params[:,i], label=labels[i], color=colors[i])

plt.legend()
plt.grid()
plt.ylabel("Displacement (mm)")
plt.xlabel("")
plt.ylim([-2.5, 2.5])
plt.text(len(mc_params[:,0])/3, 2, "Max vector displacement: " + str(round(vector_max_disp,4)) + "mm")
plt.text(len(mc_params[:,0])/3, 1.8, "Frame: " + str(vector_max_disp_i) + "/" + str(len(mc_params[:,0])))
# plt.text(len(mc_params[:,0])/2, 1.8, "param: " + param_type)
path = dir + '/../figures/displacements.svg'
plt.savefig(path, bbox_inches='tight')

# save as png too
plt.savefig(dir + '/../figures/displacements.png', bbox_inches='tight')

## PART 2 - Correlation
# dce = nib.load(dir + '/DCE.nii')
# dce_mc = nib.load(dir + '/DCE_mc.nii.gz')
# ktrans = nib.load(dir + '/dce_patlak_fit_Ktrans.nii')
# dce_data = dce.get_fdata()
# dce_mc_data = dce_mc.get_fdata()
# ktrans_data = ktrans.get_fdata()

# path2 = dir + '/bozo.png'

# mc_params (disps): 64x6
# dce_mc: 320x320x14x64
# dce_mc_data = np.reshape(dce_mc_data, (-1,64))
# bozo = corrcoef(dce_mc_data[0,0,0,:], mc_params[:,0])[0,1]

# Correlation Coefficient Image
# corr_dce = np.zeros((320,320,14,6))
# corr_dce_mc = np.zeros((320,320,14,6))
# for p in range(6):
#     for i in range(dce_mc_data.shape[0]):
#         for j in range(dce_mc_data.shape[1]):
#             for k in range(dce_mc_data.shape[2]):
#                 corr_dce[i, j, k, p] = corrcoef(dce_data[i,j,k,:], mc_params[:, p])[0,1]
#                 corr_dce_mc[i, j, k, p] = corrcoef(dce_mc_data[i ,j, k, :], mc_params[:, p])[0,1]
# final_dce = nib.Nifti1Image(corr_dce, dce.affine)
# final_dce_mc = nib.Nifti1Image(corr_dce_mc, dce_mc.affine)
# path3 = dir + '/dce_corrcoef.nii'
# path4 = dir + '/dce_mc_corrcoef.nii'
# nib.save(final_dce, path3)
# nib.save(final_dce_mc, path4)

# testing one voxel
# model = LinearRegression().fit(mc_params, dce_mc_data[87, 251, 7, :])
# r_sq = model.score(mc_params, dce_mc_data[87, 251, 7, :])
# print(r_sq)
# print(model.coef_)
# pred = model.predict(mc_params)
# residuals = (dce_mc_data[87, 251, 7, :] - pred)
# print(residuals)

# Residuals image
# dce_mc_residuals = np.zeros((320,320,14,64))
# for x in range(dce_mc_data.shape[0]):
#     for y in range(dce_mc_data.shape[1]):
#         for z in range(dce_mc_data.shape[2]):
#             model = LinearRegression(positive=True).fit(mc_params, dce_mc_data[x, y, z, :])
#             pred = model.predict(mc_params)
#             residuals = dce_mc_data[x, y, z, :] - pred
#             dce_mc_residuals[x, y, z, :] = residuals + 250


# final_dce_mc_residuals = nib.Nifti1Image(dce_mc_residuals, dce_mc.affine)
# path5 = dir + '/dce_mc_residuals_linear_150.nii'
# nib.save(final_dce_mc_residuals, path5)
#
# fig2, ax2 = plt.subplots(figsize=(10,6))
# ax2.plot(range(64), mc_params[:, 0] / mean(mc_params[:, 0]), label='param 0')
# ax2.plot(range(64), dce_mc_data[87, 251, 7, :] / mean(dce_mc_data[87, 251, 7, :]), label = 'MC SI')
# ax2.plot(range(64), residuals, label='residual')

# plt.legend()
# plt.savefig(path2, bbox_inches='tight')
