import sys
import numpy as np
from numpy.core.multiarray import unravel_index

dir = sys.argv[1]
data = np.loadtxt(dir + "/DCE_mc.nii.par", dtype = float)
max_i = data.argmax()
i = unravel_index(max_i, data.shape)
if i[1] < 3:
    print("Max displacement of " + str(data[i]) + " degrees at slice " + str(i[0]) + ", parameter " + str(i[1]))
elif i[1] == 3:
    print("Max displacement of " + str(data[i]) + " mm at slice " + str(i[0]) + ", parameter 3 (x)")
elif i[1] == 4:
    print("Max displacement of " + str(data[i]) + " mm at slice " + str(i[0]) + ", parameter 4 (y)")
elif i[1] == 5:
    print("Max displacement of " + str(data[i]) + " mm at slice " + str(i[0]) + ", parameter 5 (z)")
    