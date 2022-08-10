#!/usr/bin/env python3

import os
import argparse
from argparse import Namespace
import sys
import get_voxel_drift
import subprocess
try:
    import PySimpleGUI as sg
    gui_installed = True
except ImportError:
    gui_installed = False



def main():
    output_path = os.path.dirname(os.path.abspath(args.filename))
    os.chdir(output_path)
    
    subname = os.path.splitext(args.filename)[0] #remove .gz
    subname = os.path.splitext(subname)[0] #remove .nii
    output_name = subname+'_reg.nii'
    
    #output_name = 'S3reg.nii.gz'
    bet_name = 'S1brain.nii'
    mask_name = 'S2mask.nii'
    #delete old results if exist
    if args.overwrite:
        print('Delete previous results')
        try:
            os.remove(output_name)
            os.remove(bet_name)
            os.remove(mask_name)
        except:   
            print('') 
    
    
    #Step 1 -- Brain extraction
    print('Perform brain extration for weighting')
    #pull out single 3d dataset from 4d series
    os.system('3dAFNItoNIFTI -prefix single_set.nii.gz '+args.filename+'[0]')
    #get and save orientation
    original_orientation = subprocess.check_output("3dinfo -orient single_set.nii.gz", shell=True, universal_newlines=True).rstrip()
    print('Orientation is: ',original_orientation)
    #put in standard LPI orientation (required for brain extraction)
    os.system('3dresample -orient lpi -prefix single_set_std.nii.gz -input single_set.nii.gz')
    #perform bet
    os.system('hd-bet -i single_set_std.nii.gz')
    #return brain mask to original orientation
    os.system('3dresample -orient '+original_orientation+' -prefix '+mask_name+' -input single_set_std_bet_mask.nii.gz')
    os.system('3dresample -orient '+original_orientation+' -prefix '+bet_name+' -input single_set_std_bet.nii.gz')
    #delete intermediate files
    os.remove('single_set.nii.gz')
    os.remove('single_set_std.nii.gz')
    os.remove('single_set_std_bet.nii.gz')
    os.remove('single_set_std_bet_mask.nii.gz')

    
    #Step 2 --- Call AFNI registration
    # two pass = course fitting first, then fine fitting
    # twodup = output dataset will have its xyz-axes origins reset to those of the base dataset
    # base 0 = align everything to the first image
    # nocip = don't rescale image intensities
    # zpad = pad edges of images then remove, may help with interpolation artifacts or clipping
    # 1dfile = saves corrections to file used to make plot
    # heptic = use heptic interpolation, better than Fourier, fourier casus gibbs ringing drift artifacts
    command_txt = '3dvolreg -weight '+mask_name+'[0] -noclip -zpad 5 -1Dfile dmotion.1d -verbose -rot_thresh 0.002 -x_thresh 0.05 -maxite 50 -heptic -base 0 -prefix '+output_name+' '+args.filename
    print('Coregistration command: ',command_txt)
    os.system(command_txt)
    
    
    #Step 3 --- Create voxel drift image
    if args.makedrift:
        print('Create voxel drift image')
        get_voxel_drift.inputs(output_name,'drift_percent_reg.nii.gz')
        get_voxel_drift.run()
    
    #Step 4 --- Plot results of motion correction
    if args.showplot:
        os.system('1dplot -volreg -dx 1 -xlabel Acquisition dmotion.1d')
    
    print('Wrote motion corrected image to file: '+output_name+'.nii')
    print('Finished motion correction')
    
def inputs(filename,showplot,overwrite,makedrift):
    global args
    args=Namespace(filename=filename,showplot=showplot, overwrite=overwrite, makedrift=makedrift)
    main()
 
args=None
if __name__ == "__main__":
    if len(sys.argv)==1 and gui_installed:
        layout = [[sg.Text('Runs motion correction on a DCE dynamic series using AFNI 3dvolreg')],
                 [sg.Text('_'  * 10)],
                 [sg.Text('DCE Series', size=(10, 1)), sg.Input(), sg.FileBrowse()],      
                 [sg.Checkbox('Show 1D Motion Plot',default=True)],
                 [sg.Checkbox('Overwrite existing files',default=True)],
                 [sg.Text('Other Options:')],
                 [sg.Checkbox('Create Voxel Drift Image',default=True)],
                 [sg.Submit(), sg.Cancel()]]      

        window = sg.Window('motion_correct', layout)
        
        
        event, values = window.Read()
        window.Close()

        if event=="Cancel":
            raise SystemExit("Cancelling")
          
        print('Running motion_correct with the following inputs:')
        print("DCE Series: ",values[0])
        print("Show 1D Motion Plot: ",values[1])
        print("Overwrite existing files: ",values[2])
        print("Create Voxel Drift Image: ",values[3])
        args=Namespace(filename=values[0],showplot=values[1],overwrite=values[2],makedrift=values[3])
    else:
        if len(sys.argv)==1 and not gui_installed: 
            print('install PySimpleGUI and tkinter to use GUI, otherwise use command line options')
            print('run with "-h" to see command line options')
        parser = argparse.ArgumentParser(description='Runs motion correction on a DCE dynamic series using AFNI 3dvolreg')
        parser.add_argument('-o','--overwrite', help='Overwrite exisiting output files', action="store_true")
        parser.add_argument('-f','--filename', help='DCE series filename')
        parser.add_argument('-p','--plot', help='Show 1D Motion Plot', action="store_true")
        parser.add_argument('-d','--drift', help='Create voxel drift image', action="store_true")
        args = parser.parse_args()
    main()    