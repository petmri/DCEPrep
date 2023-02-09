#!/bin/bash


#if [[ $1 = "rat" ]]
#then
#FOV='64'
#fi

#if [[ $1 = "human" ]]
#then
FOV='256'
#fi

tkregister2 --targ $1 --mov $2 --reg Register.dat --regheader --noedit --fov $FOV

mri_vol2vol --mov $2 --targ $1 --reg Register.dat --o OutputDataset.nii.gz

fslmaths OutputDataset.nii.gz $3

echo ' '
echo '*** Registration Done ***'
echo ' '
