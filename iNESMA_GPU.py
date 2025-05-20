import nibabel as nib
import numpy as np
from numba import cuda, float32, int32
import math
import sys

def load_image(img_path):
    img = nib.load(img_path)
    data = img.get_fdata()
    return data, img

@cuda.jit
def inesma_kernel(data, smoothed_data, x_dim, y_dim, z_dim, t_dim, 
                  local_neighborhood_x, local_neighborhood_y, local_neighborhood_z, 
                  similarity_threshold, h):
    x, y, z = cuda.grid(3)
    if x < x_dim and y < y_dim and z < z_dim:
        current_curve = cuda.local.array(shape=(100,), dtype=float32)  # Adjust size as needed
        for t in range(t_dim):
            current_curve[t] = data[x, y, z, t]
        array_size=local_neighborhood_x*local_neighborhood_y*local_neighborhood_z
        similarities = cuda.local.array(shape=(1024,), dtype=float32)
        indices = cuda.local.array(shape=(1024, 3), dtype=int32)
        count = 0

        for i in range(max(0, x-local_neighborhood_x), min(x_dim, x+local_neighborhood_x+1)):
            for j in range(max(0, y-local_neighborhood_y), min(y_dim, y+local_neighborhood_y+1)):
                for k in range(max(0, z-local_neighborhood_z), min(z_dim, z+local_neighborhood_z+1)):
                    if i == x and j == y and k == z:
                        continue
                    
                    neighbor_curve = cuda.local.array(shape=(100,), dtype=float32)  # Adjust size as needed
                    for t in range(t_dim):
                        neighbor_curve[t] = data[i, j, k, t]

                    dist = 0.0
                    location = 0.0
                    for t in range(t_dim):
                        dist += (current_curve[t] - neighbor_curve[t]) ** 2
                        location += current_curve[t] ** 2
                    dist = math.sqrt(dist)
                    location = math.sqrt(location)
                    
                    #similarity = math.exp(-dist / h)
                    similarity = dist/location
                    
                    similarities[count] = similarity
                    indices[count, 0] = i
                    indices[count, 1] = j
                    indices[count, 2] = k
                    count += 1
        
        # # Find the top 5% most similar voxels
        # threshold_index = max(1, int(similarity_threshold * count))
        
        # # Manual selection sort to find top 5% similarities
        # # Uhhh, there are library functions for this....
        # for i in range(threshold_index):
        #     max_idx = i
        #     for j in range(i+1, count):
        #         if similarities[j] > similarities[max_idx]:
        #             max_idx = j
        #     if max_idx != i:
        #         # Swap values in similarities
        #         temp_similarity = similarities[i]
        #         similarities[i] = similarities[max_idx]
        #         similarities[max_idx] = temp_similarity
                
        #         # Swap values in indices
        #         temp_indices = (indices[i, 0], indices[i, 1], indices[i, 2])
        #         indices[i, 0] = indices[max_idx, 0]
        #         indices[i, 1] = indices[max_idx, 1]
        #         indices[i, 2] = indices[max_idx, 2]
        #         indices[max_idx, 0] = temp_indices[0]
        #         indices[max_idx, 1] = temp_indices[1]
        #         indices[max_idx, 2] = temp_indices[2]
        
        weighted_sum = cuda.local.array(shape=(100,), dtype=float32)  # Adjust size as needed
        for t in range(t_dim):
            weighted_sum[t] = 0.0
        normalization_factor = 0.0
        
        for idx in range(count):
            if similarities[idx] < similarity_threshold:
                # if constant_weighting:
                if h == 0:
                    similarity = 1
                else:
                    similarity = math.exp(-similarities[idx] / h)
                i = indices[idx, 0]
                j = indices[idx, 1]
                k = indices[idx, 2]
                
                neighbor_curve = cuda.local.array(shape=(100,), dtype=float32)  # Adjust size as needed
                for t in range(t_dim):
                    neighbor_curve[t] = data[i, j, k, t]
                
                for t in range(t_dim):
                    weighted_sum[t] += similarity * neighbor_curve[t]
                normalization_factor += similarity
        
        if normalization_factor != 0:
            for t in range(t_dim):
                smoothed_data[x, y, z, t] = weighted_sum[t] / normalization_factor
        else:
            for t in range(t_dim):
                smoothed_data[x, y, z, t] = current_curve[t]

def inesma_smoothing(data, num_iterations=2, local_neighborhood_x=5,local_neighborhood_y=5,local_neighborhood_z=2,
                     similarity_threshold=0.3, h=0.01):
    # num_iterations defines the number of iterations for smoothing

    # local_neighborhood defines radius in voxels of neighborhood for smoothing
    # TODO: this should be defined in mm, not in voxels

    # similarity_threshold defines the threshold to accept a voxel for smoothing

    # h defines the exponential decay of the weighting, h=0 means constant weighting
    if (local_neighborhood_x*2+1)*(local_neighborhood_y*2+1)*(local_neighborhood_z*2+1) > 1024:
        raise ValueError("The neighborhood size exceeds the fixed array size in the kernel. Adjust the array size in the kernel.")

    x_dim, y_dim, z_dim, t_dim = data.shape
    smoothed_data = np.copy(data)
    
    data_device = cuda.to_device(data)
    smoothed_data_device = cuda.to_device(smoothed_data)
    
    threads_per_block = (8, 8, 8)
    blocks_per_grid_x = (x_dim + threads_per_block[0] - 1) // threads_per_block[0]
    blocks_per_grid_y = (y_dim + threads_per_block[1] - 1) // threads_per_block[1]
    blocks_per_grid_z = (z_dim + threads_per_block[2] - 1) // threads_per_block[2]
    
    for _ in range(num_iterations):
        inesma_kernel[(blocks_per_grid_x, blocks_per_grid_y, blocks_per_grid_z), threads_per_block](
            data_device, smoothed_data_device, x_dim, y_dim, z_dim, t_dim, 
            local_neighborhood_x, local_neighborhood_y, local_neighborhood_z,
            similarity_threshold, h
        )
        data_device = cuda.to_device(smoothed_data_device.copy_to_host())
    
    smoothed_data = smoothed_data_device.copy_to_host()
    return smoothed_data

# Load and smooth the image
prefix = sys.argv[1]
img_path = sys.argv[2]
data, img = load_image(img_path)

roi_path = sys.argv[3]
roi_data, roi_img = load_image(roi_path)

# expand roi_data to 4D and match the shape of data
# roi_data = np.expand_dims(roi_data, axis=3)
# roi_data = np.repeat(roi_data, data.shape[3], axis=3)

# save data where roi_data > 0
data_restore = np.copy(data)
data_restore[roi_data == 0] = 0

# exclude roi_data from data
data[roi_data > 0] = 0

# Ensure t_dim does not exceed the array size in the kernel
t_dim = data.shape[3]
if t_dim > 100:
    raise ValueError("The time dimension (t_dim) exceeds the fixed array size in the kernel. Adjust the array size in the kernel.")

# normalize the data robustly (2nd and 98th percentile)
p2 = np.percentile(data, 2)
p98 = np.percentile(data, 98)
data = np.clip(data, p2, p98)
data = (data - p2) / (p98 - p2)

# SHMOOOTHING
smoothed_data = inesma_smoothing(data)

# Restore roi in smoothed data
smoothed_data[roi_data > 0] = data_restore[roi_data > 0]

# Save the smoothed image
smoothed_img = nib.Nifti1Image(smoothed_data, img.affine, img.header)
nib.save(smoothed_img, f'dce/{prefix}_desc-bfczSmoothed_DCE.nii.gz')
