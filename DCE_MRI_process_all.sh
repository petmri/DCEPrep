#!/bin/bash
# FSL, AFNI, Matlab, ROCKETSHIP + parametric_scripts, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
EN_Z_NORM=0
EN_BIAS1=0
EN_BIAS2=0
EN_MOTION_CORR=1
ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)

# cd to your main data directory
cd /media/network_mriphysics/LLUCAS-USC/data

# Generate bias corrected data for every subject timepoint
for dir in */*_timepoint/; do
	date
	echo Processing ${dir}...
	SUBJECT_TP_PATH=$(realpath $dir)
	
	cd $dir
	# FSL brain mask extraction from VFA 2 image
	bet 2.nii brain.nii -R -m -f 0.45 -g 0 -Z
	fslcpgeom 2.nii brain_mask.nii
	
	if [ $EN_BIAS1 -eq 1 ]
		then
		echo Bias field correction with FAST
		# don't forget to remove all unnecessary images 
		fast -t 3 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 2.nii
		rm 2_mixeltype.nii.gz
		rm 2_pve_0.nii.gz
		rm 2_pve_1.nii.gz
		rm 2_pve_2.nii.gz
		rm 2_pveseg.nii.gz
		rm 2_seg.nii.gz
		3dcalc -a 2.nii -b 2_bias.nii.gz -expr a/b -prefix 2_bfc.nii
		
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 5.nii
		rm 5_mixeltype.nii.gz
		rm 5_pve_0.nii.gz
		rm 5_pve_1.nii.gz
		rm 5_pve_2.nii.gz
		rm 5_pveseg.nii.gz
		rm 5_seg.nii.gz
		3dcalc -a 5.nii -b 5_bias.nii.gz -expr a/b -prefix 5_bfc.nii

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 10.nii
		rm 10_mixeltype.nii.gz
		rm 10_pve_0.nii.gz
		rm 10_pve_1.nii.gz
		rm 10_pve_2.nii.gz
		rm 10_pveseg.nii.gz
		rm 10_seg.nii.gz
		3dcalc -a 10.nii -b 10_bias.nii.gz -expr a/b -prefix 10_bfc.nii

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 12.nii
		rm 12_mixeltype.nii.gz
		rm 12_pve_0.nii.gz
		rm 12_pve_1.nii.gz
		rm 12_pve_2.nii.gz
		rm 12_pveseg.nii.gz
		rm 12_seg.nii.gz
		3dcalc -a 12.nii -b 12_bias.nii.gz -expr a/b -prefix 12_bfc.nii

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 15.nii
		rm 15_mixeltype.nii.gz
		#rm 15_pve_0.nii.gz
		#rm 15_pve_1.nii.gz
		#rm 15_pve_2.nii.gz
		rm 15_pveseg.nii.gz
		rm 15_seg.nii.gz
		3dcalc -a 15.nii -b 15_bias.nii.gz -expr a/b -prefix 15_bfc.nii
			
		fslmaths 2_bfc.nii -mas brain_mask.nii.gz 2_b1corr.nii
		fslmaths 5_bfc.nii -mas brain_mask.nii.gz 5_b1corr.nii
		fslmaths 10_bfc.nii -mas brain_mask.nii.gz 10_b1corr.nii
		fslmaths 12_bfc.nii -mas brain_mask.nii.gz 12_b1corr.nii
		fslmaths 15_bfc.nii -mas brain_mask.nii.gz 15_b1corr.nii
	else
		echo Skipping BFC...
		# mask existing data
		fslmaths 2.nii -mas brain_mask.nii.gz 2_b1corr.nii 
		fslmaths 5.nii -mas brain_mask.nii.gz 5_b1corr.nii
		fslmaths 10.nii -mas brain_mask.nii.gz 10_b1corr.nii
		fslmaths 12.nii -mas brain_mask.nii.gz 12_b1corr.nii
		fslmaths 15.nii -mas brain_mask.nii.gz 15_b1corr.nii
	fi
	
	# unzip because sometimes they're zipped
	gunzip 2_b1corr.nii.gz
	gunzip 5_b1corr.nii.gz
	gunzip 10_b1corr.nii.gz
	gunzip 12_b1corr.nii.gz
	gunzip 15_b1corr.nii.gz
	
	# clean up
	#rm 2_b1corr.nii.gz
	#rm 5_b1corr.nii.gz
	#rm 10_b1corr.nii.gz
	#rm 12_b1corr.nii.gz
	#rm 15_b1corr.nii.gz
done

# Z-axis normalization - all subjects
if [ $EN_Z_NORM -eq 1 ] 
	then
	cd ../..
	echo Z-normalization on ALL subjects
	python3 python_norm1.py
	cd $dir
fi

# process normalized data
for dir in */*_timepoint/; do
	if [ $EN_BIAS2 -eq 1 ]
		then
		echo Begin second round of BFC
		# WE GO AGANE
		# Bias field correction with FAST
		# don't forget to remove all unnecessary images 
		fast -t 3 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 2_corr_finalZ.nii
		rm 2_corr_finalZ_mixeltype.nii.gz
		rm 2_corr_finalZ_pve_0.nii.gz
		rm 2_corr_finalZ_pve_1.nii.gz
		rm 2_corr_finalZ_pve_2.nii.gz
		rm 2_corr_finalZ_pveseg.nii.gz
		rm 2_corr_finalZ_seg.nii.gz
		3dcalc -a 2_corr_finalZ.nii -b 2_corr_finalZ_bias.nii.gz -expr a/b -prefix 2_b2corr.nii
		#fslmaths 2_b1corr.nii -mas brain_mask.nii.gz 2_new.nii 
		
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 5_corr_finalZ.nii
		rm 5_corr_finalZ_mixeltype.nii.gz
		rm 5_corr_finalZ_pve_0.nii.gz
		rm 5_corr_finalZ_pve_1.nii.gz
		rm 5_corr_finalZ_pve_2.nii.gz
		rm 5_corr_finalZ_pveseg.nii.gz
		rm 5_corr_finalZ_seg.nii.gz
		3dcalc -a 5_corr_finalZ.nii -b 5_corr_finalZ_bias.nii.gz -expr a/b -prefix 5_b2corr.nii
		#fslmaths 5_b1corr.nii -mas brain_mask.nii.gz 5_new.nii 

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 10_corr_finalZ.nii
		rm 10_corr_finalZ_mixeltype.nii.gz
		rm 10_corr_finalZ_pve_0.nii.gz
		rm 10_corr_finalZ_pve_1.nii.gz
		rm 10_corr_finalZ_pve_2.nii.gz
		rm 10_corr_finalZ_pveseg.nii.gz
		rm 10_corr_finalZ_seg.nii.gz
		3dcalc -a 10_corr_finalZ.nii -b 10_corr_finalZ_bias.nii.gz -expr a/b -prefix 10_b2corr.nii
		#fslmaths 10_b1corr.nii -mas brain_mask.nii.gz 10_new.nii 

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 12_corr_finalZ.nii
		rm 12_corr_finalZ_mixeltype.nii.gz
		rm 12_corr_finalZ_pve_0.nii.gz
		rm 12_corr_finalZ_pve_1.nii.gz
		rm 12_corr_finalZ_pve_2.nii.gz
		rm 12_corr_finalZ_pveseg.nii.gz
		rm 12_corr_finalZ_seg.nii.gz
		3dcalc -a 12_corr_finalZ.nii -b 12_corr_finalZ_bias.nii.gz -expr a/b -prefix 12_b2corr.nii
		#fslmaths 12_b1corr.nii -mas brain_mask.nii.gz 12_new.nii 

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 15_corr_finalZ.nii
		rm 15_corr_finalZ_mixeltype.nii.gz
		rm 15_corr_finalZ_pve_0.nii.gz
		rm 15_corr_finalZ_pve_1.nii.gz
		rm 15_corr_finalZ_pve_2.nii.gz
		rm 15_corr_finalZ_pveseg.nii.gz
		rm 15_corr_finalZ_seg.nii.gz
		3dcalc -a 15_corr_finalZ.nii -b 15_corr_finalZ_bias.nii.gz -expr a/b -prefix 15_b2corr.nii
		#fslmaths 15_b1corr.nii -mas brain_mask.nii.gz 15_new.nii 
		
		# concatenates 5 images in one VFA.nii image  
		3dTcat -prefix VFA.nii 2_b2corr.nii 5_b2corr.nii 10_b2corr.nii 12_b2corr.nii 15_b2corr.nii
	elif [ $EN_Z_NORM -eq 1 ] 
		then
		echo Concatenating Z-norm\'d images
		# concatenates 5 images in one VFA.nii image
		3dTcat -prefix VFA.nii 2_corr_finalZ.nii 5_corr_finalZ.nii 10_corr_finalZ.nii 12_corr_finalZ.nii 15_corr_finalZ.nii

	else
		echo Concatenating non Z\'d images
		3dTcat -prefix VFA.nii 2_b1corr.nii 5_b1corr.nii 10_b1corr.nii 12_b1corr.nii 15_b1corr.nii
	fi
	
	# motion correction of VFA
	3dvolreg -heptic -verbose -base 'VFA.nii[0]' -dfile VFA_motion.txt -prefix VFA.motioncorrected.nii VFA.nii

	# T1 mapping where the input image is 'VFA.motioncorrected.nii'
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH/parametric_scripts/custom_scripts'); T1mapping_fit('$SUBJECT_TP_PATH/'); exit;"
	#matlab -nodisplay -r "cd('/home/mrispec/Code/ROCKETSHIP/parametric_scripts/custom_scripts'); T1mapping_fit('/home/mrispec/Desktop/raw_data/1101428_2nd_version/1st_timepoint/'); exit;"
	
	# Motion correction of DCE-MRI images using AFNI
	if [ $EN_BIAS1 -eq 1 ]
		then
		echo Applying BFC to dynamic set
		3dvolreg -heptic -verbose -base 'DCE.nii[1]' -dfile DCE_motion.txt -prefix DCE.motioncorrected.nii DCE.nii
		
		3dTcat -prefix ref_rep.nii DCE.motioncorrected.nii'[1]'
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
	else
		echo Motion correcting dynamic set
		3dvolreg -heptic -verbose -base 'DCE.nii[1]' -dfile DCE_motion.txt -prefix dce_mc_b1_corr.nii DCE.nii
		3dTcat -prefix ref_rep.nii dce_mc_b1_corr.nii'[1]'
	fi
	#rm ref_rep.nii
	
	# Align T1 map with Dynamic data, quick and dirty
	flirt -in T1_map_t1_fa_linear_fit_VFA.motioncorrected.nii -ref ref_rep.nii -out t1_map_fixed_use_me.nii -omat t12dcevol.mat -dof 6 -inweight brain_mask.nii.gz

	# DCE
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH'); run_dce_auto('$SUBJECT_TP_PATH/'); exit;"
	cd ../../	
	echo $dir processing complete!
done

