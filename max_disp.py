import sys
import numpy as np
from numpy.core.multiarray import unravel_index

dir = sys.argv[1]
data = np.loadtxt(dir + "/DCE_mc.nii.par", dtype = float)
data[:,0:3] = data[:,0:3]*50
max_i = data.argmax()
i = unravel_index(max_i, data.shape)
print("Max displacement of " + str(data[i]) + " mm at time slice " + str(i[0] + 1) + "/64, parameter " + str(i[1]))
