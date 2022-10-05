#!/bin/bash

3dAFNItoNIFTI -prefix TempDataset1.nii.gz $1
3dAFNItoNIFTI -prefix TempDataset2.nii.gz $2

#if [[ $1 = "rat" ]]
#then
#FOV='64'
#fi

#if [[ $1 = "human" ]]
#then
FOV='256'
#fi

tkregister2 --targ TempDataset1.nii.gz --mov TempDataset2.nii.gz --reg Register.dat --regheader --noedit --fov $FOV

mri_vol2vol --mov TempDataset2.nii.gz --targ TempDataset1.nii.gz --reg Register.dat --o OutputDataset.nii.gz

3dcalc -a OutputDataset.nii.gz -expr 'a' -prefix $3 -overwrite

rm TempDataset*
rm OutputDataset*

echo ' '
echo '*** Registration Done ***'
echo ' '
