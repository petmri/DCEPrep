import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt


cpu_file = '/media/network_mriphysics/GRASP/500181/DCE_2cxm_cpu/DCEBBB_flip_500181-2slices_2cxm_fit_Ktrans.nii'
gpu_file = '/media/network_mriphysics/GRASP/500181/DCE_2cxm/DCEBBB_flip_500181-2slices_2cxm_fit_Ktrans.nii'

print('Processing file: '+cpu_file)
cpu_img = nib.load(cpu_file)
cpu_img_data = cpu_img.get_data()

print('Processing file: '+gpu_file)
gpu_img = nib.load(gpu_file)
gpu_img_data = gpu_img.get_data()


gpu_filter = gpu_img_data[cpu_img_data>0]
cpu_filter = cpu_img_data[cpu_img_data>0]
cpu_filter = cpu_filter[gpu_filter>0]
gpu_filter = gpu_filter[gpu_filter>0]

gpu_filter = gpu_filter[cpu_filter<0.1]
cpu_filter = cpu_filter[cpu_filter<0.1]
cpu_filter = cpu_filter[gpu_filter<0.1]
gpu_filter = gpu_filter[gpu_filter<0.1]

gpu_small = gpu_filter[::50]
cpu_small = cpu_filter[::50]

print("Total voxels: ",gpu_img_data.size)
print("Filtered voxels (median): ",cpu_filter.size)
print("Plot voxels: ",cpu_small.size)

difference = np.subtract(gpu_filter,cpu_filter)
diff_abs = np.abs(difference)
diff_median = np.median(diff_abs)
diff_mean = np.mean(diff_abs)
print("Median difference: ",diff_median)
print("Mean difference: ",diff_mean)

plt.rcParams.update({'font.size': 16})
plt.figure()
ax = plt.axes()
plt.scatter(cpu_small,gpu_small,marker='o',s=10)
#plt.plot(age_list_short,naa_list_short,'o', xx, yy)
plt.title('2CXM DCE Fitting')
plt.xlabel('Ktrans (CPU - Matlab)')
plt.ylabel('Ktrans (GPU - GPUFit)')
ax.set_ylim([0, 0.1])
ax.set_xlim([0, 0.1])

plt.show()