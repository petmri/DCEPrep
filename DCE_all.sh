#!/bin/bash
# Oct 13, 2022
# FSL, AFNI, Matlab, ROCKETSHIP + parametric_scripts, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
# control variables
EN_Z_NORM=0
EN_BIAS1=1
EN_BIAS2=0
ff=0
#EN_MOTION_CORR=1

# make this your main data directory or pass it as an option to -d
#DATA_DIR=/media/network_mriphysics/USC-PPG/data

# options
while getopts ":d:bBZFh" options; do
	case "${options}" in
		b)
			EN_BIAS1=1
			;;
		B)	EN_BIAS2=1
			;;
		d)
			DATA_DIR=${OPTARG}
			;;
		F)
			ff=1
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, processing every folder ending in '_timepoint'."
			echo "The output is mainly the DCE outputs (Ktrans maps) and QC graphs."
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-Z: enable Z-slice normalization"
			echo "-d: specify main data directory containing all subject folders"
			echo "-F: fail fast, any command failures will end the script"
			echo "-h: display this message"
			exit 0
			;;
		Z)
			EN_Z_NORM=1
			;;
	esac
done

if [ -z "$DATA_DIR" ]
	then
		echo "ERROR: Please use '-d [dir_path]' to pass the path to your main data directory to this script."
		exit 1
fi
cd $DATA_DIR
ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(find $HOME -name '*run_dce_auto.m' -printf '%h\n' -quit)
	SCRIPT_PATH=$(find $HOME -name '*auto_analysis.py' -printf '%h\n' -quit)
fi

# Run bias correction on VFA data 
# ------------------------------
for dir in */*_timepoint/; do
	date
	echo DCE processing ${dir}...
	SUBJECT_TP_PATH=$(realpath $dir)
	cd $dir

	# ensure AIF is included in mask
	fslcpgeom 2.nii brain_mask_dyn.nii
	cp aif.nii aif_aligned.nii
	fslcpgeom brain_mask_dyn.nii aif_aligned.nii
	fslmaths aif_aligned.nii -thr 0 aif_pos.nii
	rm aif_aligned.nii
	fslmaths brain_mask_dyn.nii -add aif_pos.nii -thr 1 -bin brain_mask_dyn_aif.nii
	fslmaths DCE_mc.nii -mas brain_mask_dyn_aif.nii.gz DCE_mc_masked.nii
		
	if [ $EN_BIAS1 -eq 1 ]
		then
		if [ ! -f "DCE_mc_bfc.nii" ]
			then
			# Applying bias field correction on dynamic images
			# ------------------------------
			echo Applying BFC to dynamic images...
			3dTcat -prefix 1st_rep.nii DCE_mc_masked.nii'[0]' -overwrite # extract images from different DCE repetitions
			3dTcat -prefix 5th_rep.nii DCE_mc_masked.nii'[4]' -overwrite
			3dTcat -prefix 10th_rep.nii DCE_mc_masked.nii'[9]' -overwrite
			3dTcat -prefix 20th_rep.nii DCE_mc_masked.nii'[19]' -overwrite
			3dTcat -prefix 30th_rep.nii DCE_mc_masked.nii'[29]' -overwrite
			3dTcat -prefix 40th_rep.nii DCE_mc_masked.nii'[39]' -overwrite
			3dTcat -prefix 50th_rep.nii DCE_mc_masked.nii'[49]' -overwrite
			3dTcat -prefix 60th_rep.nii DCE_mc_masked.nii'[59]' -overwrite
	
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
			3dTcat -prefix dyn_bias.nii 1st_rep_bias.nii.gz 5th_rep_bias.nii.gz 10th_rep_bias.nii.gz 20th_rep_bias.nii.gz 30th_rep_bias.nii.gz 40th_rep_bias.nii.gz 50th_rep_bias.nii.gz 60th_rep_bias.nii.gz -overwrite
	
			# Computing average across 8 bias field that have been sampled
			3dTstat -mean -prefix mean_dyn_bias_map.nii dyn_bias.nii'[0..7]' -overwrite
	
			# Normalizing motion corrected DCE image with mean bias field 
			3dcalc -a DCE_mc_masked.nii -b mean_dyn_bias_map.nii -expr a/b -prefix DCE_mc_bfc.nii -overwrite
	
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
			echo Skipping DCE BFC...
		fi
	else
		#echo Motion correcting dynamic set
		#3dvolreg -heptic -verbose -base 'DCE.nii[1]' -dfile DCE_motion.txt -prefix DCE_mc_bfc.nii DCE.nii
		#3dTcat -prefix ref_rep.nii dce_mc_bfc'[1]'
		gunzip -f DCE_mc.nii.gz
		mv DCE_mc.nii DCE_mc_bfc.nii
	fi
	
	# align existing white matter mask to dynamic images and re-binarize
	bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii 15_wm.nii.gz 15_wm_mask_dyn.nii.gz
	fslmaths 15_wm_mask_dyn.nii.gz -thr 1.7 -bin 15_wm_mask_dyn.nii
	
	# apply wm mask to all DCE images
	fslmaths DCE_mc_bfc.nii -mas 15_wm_mask_dyn.nii.gz DCE_mc_bfc_wm.nii.gz

	# normalize dynamic images
	# ------------------------------
	echo Normalizing dynamic images...
	python3 $SCRIPT_PATH/DCE_norm.py $SUBJECT_TP_PATH
	if [ $ff -eq 1 ]
		then
			if [ ! -f "DCE_mc_bfc_norm.nii" ]
				then
					echo "Missing normalized DCE file."
					fail=1
					cd ../..
					continue
			fi
	fi
	# smooth dynamic set
	#3dBlurToFWHM -input DCE_mc_bfc_norm.nii -FWHM 4 -prefix DCE_mc_bfc_norm_blurred.nii

	# DCE
	# ------------------------------
	echo Begin DCE processing...
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH'); addpath '$GPUFIT_PATH/matlab'; run_dce_auto('$SUBJECT_TP_PATH/'); exit;"

	if [ $ff -eq 1 ]
		then
			if [ ! -f "dce_patlak_fit_Ktrans.nii" ]
				then
					echo "Missing Ktrans maps. Check terminal--DCE failed or inputs were not generated."
					fail=1
					continue
			fi
	fi
	
	# Analyze results (scouting)
	# ------------------------------
	# Make gm mask
	if [ $EN_BIAS1 -eq 1 ]
		then
		fslmaths 15_masked_seg.nii.gz -thr 2 -uthr 2 -bin 15_gm_mask.nii
		fslmaths 15_bfc.nii -mas 15_gm_mask.nii.gz 15_gm.nii
	else
		fslmaths 15_bfc_seg.nii.gz -thr 2 -uthr 2 -bin 15_gm_mask.nii
		fslmaths 15_bfc.nii -mas 15_gm_mask.nii.gz 15_gm.nii
	fi
	
	# Align then re-binarize gm mask
	bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii 15_gm.nii.gz 15_gm_mask_dyn.nii.gz
	fslmaths 15_gm_mask_dyn.nii.gz -thr 20 -bin 15_gm_mask_dyn.nii
	
	# Make CSF mask
	if [ $EN_BIAS1 -eq 1 ]
		then
		fslmaths 15_masked_seg.nii.gz -thr 1 -uthr 1 -bin 15_csf_mask.nii
		fslmaths 15_bfc.nii -mas 15_csf_mask.nii.gz 15_csf.nii
	else
		fslmaths 15_bfc_seg.nii.gz -thr 1 -uthr 1 -bin 15_csf_mask.nii
		fslmaths 15_bfc.nii -mas 15_csf_mask.nii.gz 15_csf.nii
	fi
	
	# Align CSF mask
	flirt -in 15_csf.nii.gz -ref ref_rep.nii -out 15_csf_mask_dyn.nii.gz -init t12dcevol.mat -applyxfm
	bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii 15_csf.nii.gz 15_csf_mask_dyn.nii.gz
	fslmaths 15_csf_mask_dyn.nii.gz -thr 20 -bin 15_csf_mask_dyn.nii
	
	# Apply masks to T1 map
	fslmaths t1_map_fixed_use_me.nii.gz -mas 15_wm_mask_dyn.nii T1_wm.nii
	fslmaths t1_map_fixed_use_me.nii.gz -mas 15_gm_mask_dyn.nii T1_gm.nii
	fslmaths t1_map_fixed_use_me.nii.gz -mas 15_csf_mask_dyn.nii T1_csf.nii
	
	# Apply masks to Ktrans map
	fslmaths dce_patlak_fit_Ktrans.nii -mas 15_wm_mask_dyn.nii Ktrans_wm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas 15_gm_mask_dyn.nii Ktrans_gm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas 15_csf_mask_dyn.nii Ktrans_csf.nii
	
	python3 $SCRIPT_PATH/auto_analysis.py $SUBJECT_TP_PATH
	python3 $SCRIPT_PATH/report.py $SUBJECT_TP_PATH
	cd ../../	
	echo $dir processing complete!
done
