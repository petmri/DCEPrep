#!/bin/bash
# FSL, AFNI, Matlab, ROCKETSHIP + parametric_scripts, and Python are required
# PLACE THIS SCRIPT IN MAIN DATA DIRECTORY
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)

# Process data in every subject timepoint directory
for dir in */*_timepoint/; do
	echo Processing ${dir}...
	SUBJECT_TP_PATH=$(realpath $dir)
	
	cd $dir
	# FSL brain mask extraction from VFA 2 image
	bet 2.nii brain.nii -R -m -f 0.45 -g 0

	# Bias field correction with FAST
	# don't forget to remove all unnecessary images 
	fast -t 3 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 2.nii
	rm 2_mixeltype.nii.gz
	rm 2_pve_0.nii.gz
	rm 2_pve_1.nii.gz
	rm 2_pve_2.nii.gz
	rm 2_pveseg.nii.gz
	rm 2_seg.nii.gz
	3dcalc -a 2.nii -b 2_bias.nii.gz -expr a/b -prefix 2_b1corr.nii
	fslmaths 2_b1corr.nii -mas brain_mask.nii.gz 2_new.nii 
	
	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 5.nii
	rm 5_mixeltype.nii.gz
	rm 5_pve_0.nii.gz
	rm 5_pve_1.nii.gz
	rm 5_pve_2.nii.gz
	rm 5_pveseg.nii.gz
	rm 5_seg.nii.gz
	3dcalc -a 5.nii -b 5_bias.nii.gz -expr a/b -prefix 5_b1corr.nii
	fslmaths 5_b1corr.nii -mas brain_mask.nii.gz 5_new.nii 

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 10.nii
	rm 10_mixeltype.nii.gz
	rm 10_pve_0.nii.gz
	rm 10_pve_1.nii.gz
	rm 10_pve_2.nii.gz
	rm 10_pveseg.nii.gz
	rm 10_seg.nii.gz
	3dcalc -a 10.nii -b 10_bias.nii.gz -expr a/b -prefix 10_b1corr.nii
	fslmaths 10_b1corr.nii -mas brain_mask.nii.gz 10_new.nii 

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 12.nii
	rm 12_mixeltype.nii.gz
	rm 12_pve_0.nii.gz
	rm 12_pve_1.nii.gz
	rm 12_pve_2.nii.gz
	rm 12_pveseg.nii.gz
	rm 12_seg.nii.gz
	3dcalc -a 12.nii -b 12_bias.nii.gz -expr a/b -prefix 12_b1corr.nii
	fslmaths 12_b1corr.nii -mas brain_mask.nii.gz 12_new.nii 

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 15.nii
	rm 15_mixeltype.nii.gz
	rm 15_pve_0.nii.gz
	rm 15_pve_1.nii.gz
	rm 15_pve_2.nii.gz
	rm 15_pveseg.nii.gz
	rm 15_seg.nii.gz
	3dcalc -a 15.nii -b 15_bias.nii.gz -expr a/b -prefix 15_b1corr.nii
	fslmaths 15_b1corr.nii -mas brain_mask.nii.gz 15_new.nii 
	
	# Z-axis normalization - all VFA images
	cd ../..
	python3 python_norm1.py
	cd $dir
	
	# concatenates 5 images in one VFA.nii image  
	3dTcat -prefix VFA.nii 2_corr_finalZ.nii 5_corr_finalZ.nii 10_corr_finalZ.nii 12_corr_finalZ.nii 15_corr_finalZ.nii

	# motion correction throughout Z axis  
	3dvolreg -Fourier -verbose -base 'VFA.nii[0]' -dfile VFA_motion.txt -prefix VFA.motioncorrected.nii VFA.nii

	# T1 mapping where the input image is 'VFA.motioncorrected.nii'
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH/parametric_scripts/custom_scripts'); T1mapping_fit('$SUBJECT_TP_PATH/'); exit;"

	# Motion correction of DCE-MRI images using AFNI
	3dvolreg -Fourier -verbose -base 'DCE.nii[1]' -dfile DCE_motion.txt -prefix DCE.motioncorrected.nii DCE.nii

	# Applying pseudo-dynamic bias field correction on dynamic images
	3dTcat -prefix 1st_rep.nii DCE.motioncorrected.nii'[0]' # extract images from different DCE repetitions 
	3dTcat -prefix 5th_rep.nii DCE.motioncorrected.nii'[4]'
	3dTcat -prefix 10th_rep.nii DCE.motioncorrected.nii'[9]'
	3dTcat -prefix 20th_rep.nii DCE.motioncorrected.nii'[19]'
	3dTcat -prefix 30th_rep.nii DCE.motioncorrected.nii'[29]'
	3dTcat -prefix 40th_rep.nii DCE.motioncorrected.nii'[39]'
	3dTcat -prefix 50th_rep.nii DCE.motioncorrected.nii'[49]'
	3dTcat -prefix 60th_rep.nii DCE.motioncorrected.nii'[59]'

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 1st_rep.nii
	rm 1st_rep_mixeltype.nii.gz
	rm 1st_rep_pve_0.nii.gz
	rm 1st_rep_pve_1.nii.gz
	rm 1st_rep_pve_2.nii.gz
	rm 1st_rep_pveseg.nii.gz
	rm 1st_rep_seg.nii.gz

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 5th_rep.nii
	rm 5th_rep_mixeltype.nii.gz
	rm 5th_rep_pve_0.nii.gz
	rm 5th_rep_pve_1.nii.gz
	rm 5th_rep_pve_2.nii.gz
	rm 5th_rep_pveseg.nii.gz
	rm 5th_rep_seg.nii.gz

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 10th_rep.nii
	rm 10th_rep_mixeltype.nii.gz
	rm 10th_rep_pve_0.nii.gz
	rm 10th_rep_pve_1.nii.gz
	rm 10th_rep_pve_2.nii.gz
	rm 10th_rep_pveseg.nii.gz
	rm 10th_rep_seg.nii.gz

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 20th_rep.nii
	rm 20th_rep_mixeltype.nii.gz
	rm 20th_rep_pve_0.nii.gz
	rm 20th_rep_pve_1.nii.gz
	rm 20th_rep_pve_2.nii.gz
	rm 20th_rep_pveseg.nii.gz
	rm 20th_rep_seg.nii.gz

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 30th_rep.nii
	rm 30th_rep_mixeltype.nii.gz
	rm 30th_rep_pve_0.nii.gz
	rm 30th_rep_pve_1.nii.gz
	rm 30th_rep_pve_2.nii.gz
	rm 30th_rep_pveseg.nii.gz
	rm 30th_rep_seg.nii.gz

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 40th_rep.nii
	rm 40th_rep_mixeltype.nii.gz
	rm 40th_rep_pve_0.nii.gz
	rm 40th_rep_pve_1.nii.gz
	rm 40th_rep_pve_2.nii.gz
	rm 40th_rep_pveseg.nii.gz
	rm 40th_rep_seg.nii.gz

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 50th_rep.nii
	rm 50th_rep_mixeltype.nii.gz
	rm 50th_rep_pve_0.nii.gz
	rm 50th_rep_pve_1.nii.gz
	rm 50th_rep_pve_2.nii.gz
	rm 50th_rep_pveseg.nii.gz
	rm 50th_rep_seg.nii.gz

	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 60th_rep.nii
	rm 60th_rep_mixeltype.nii.gz
	rm 60th_rep_pve_0.nii.gz
	rm 60th_rep_pve_1.nii.gz
	rm 60th_rep_pve_2.nii.gz
	rm 60th_rep_pveseg.nii.gz
	rm 60th_rep_seg.nii.gz

	# Concatenation1
	3dTcat -prefix dyn_bias.nii 1st_rep_bias.nii.gz 5th_rep_bias.nii.gz 10th_rep_bias.nii.gz 20th_rep_bias.nii.gz 30th_rep_bias.nii.gz 40th_rep_bias.nii.gz 50th_rep_bias.nii.gz 60th_rep_bias.nii.gz 

	# Computing average across 8 bias field that have been sampled
	3dTstat -mean -prefix mean_dyn_bias_map.nii dyn_bias.nii'[0..7]'

	# Normalizing motion corrected DCE image with mean bias field 
	3dcalc -a DCE.motioncorrected.nii -b mean_dyn_bias_map.nii -expr a/b -prefix dce_mc_b1_corr.nii

	# don't forget to remove all unnecessary images 
	rm 1st_rep.nii
	rm 1st_rep_bias.nii.gz
	rm 5th_rep.nii
	rm 5th_rep_bias.nii.gz
	rm 10th_rep.nii
	rm 10th_rep_bias.nii.gz
	rm 20th_rep.nii
	rm 20th_rep_bias.nii.gz
	rm 30th_rep.nii
	rm 30th_rep_bias.nii.gz
	rm 40th_rep.nii
	rm 40th_rep_bias.nii.gz
	rm 50th_rep.nii
	rm 50th_rep_bias.nii.gz
	rm 60th_rep.nii
	rm 60th_rep_bias.nii.gz

	# DCE
	matlab -nodisplay -nosplash -nodesktop -r "cd('$ROCKETSHIP_PATH'); run_dce_auto('$SUBJECT_TP_PATH/'); exit;"
	cd ../../	
	echo $dir processing complete!
done

