#!/usr/bin/env python3

import numpy as np
import nibabel as nib
import os
import argparse
from argparse import Namespace

def run(): 
    #filename = '/media/network_mriphysics/GRASP/test/400105.nii.gz'
    #filename = '/media/network_mriphysics/GRASP/test/S3reg_strip_auto_threshold.nii'
    #output_dir = '/media/network_mriphysics/GRASP/test/'
    
    img = nib.load(args.filename)
    
    print('Data read with dimensions ',img.shape)
    
    data = img.get_fdata()
    
    #Prep variables for linear fitting
    x = np.arange(0,img.shape[3])
    A = np.vstack([x, np.ones(len(x))]).T
    
    y = np.reshape(data,(img.shape[0]*img.shape[1]*img.shape[2],img.shape[3])).T
    
    #Do Fit
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    drift = np.divide(m,c)
    drift = np.multiply(drift,100*img.shape[3])
    
    drift_array = np.reshape(drift,(img.shape[0],img.shape[1],img.shape[2]))
    
    
    #Write drift file
    img = nib.Nifti1Image(drift_array,np.eye(4))
    #img.header.set_zooms((size_x,size_y,size_z))
    #img.header.set_xyzt_units('mm','sec')
    img.to_filename(args.savename)
    print('Wrote file to: '+args.savename)


def inputs(filename,savename):
    global args
    args=Namespace(filename=filename, savename=savename)
    run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linear fit (over time) of every voxel, outputs percent change')
    parser.add_argument('-f','--filename', help='dynamic series filename')
    parser.add_argument('-s','--savename', help='output filename')
    args = parser.parse_args()
    run()  


