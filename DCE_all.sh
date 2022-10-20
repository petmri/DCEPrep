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

for dir in */*_timepoint/; do
	date
	echo DCE processing ${dir}...
	cd $dir
	SUBJECT_TP_PATH=$(pwd)

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
	
	# Analyze results
	# ------------------------------
	
	# Align then re-binarize gm mask
	bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii segmented_t1_seg_1.nii.gz T1_gm_dyn.nii.gz
	#fslmaths 15_gm_mask_dyn.nii.gz -thr 20 -bin 15_gm_mask_dyn.nii
	
	
	# Align CSF mask
	#flirt -in 15_csf.nii.gz -ref ref_rep.nii -out 15_csf_mask_dyn.nii.gz -init t12dcevol.mat -applyxfm
	bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii segmented_t1_seg_0.nii.gz T1_csf_dyn.nii.gz
	#fslmaths 15_csf_mask_dyn.nii.gz -thr 20 -bin 15_csf_mask_dyn.nii
	
	# Apply masks to T1 map
	fslmaths t1_map_fixed_use_me.nii.gz -mas T1_wm_dyn.nii T1_wm.nii
	fslmaths t1_map_fixed_use_me.nii.gz -mas T1_gm_dyn.nii T1_gm.nii
	fslmaths t1_map_fixed_use_me.nii.gz -mas T1_csf_dyn.nii T1_csf.nii
	
	# Apply masks to Ktrans map
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_wm_dyn.nii Ktrans_wm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_gm_dyn.nii Ktrans_gm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_csf_dyn.nii Ktrans_csf.nii
	
	python3 $SCRIPT_PATH/auto_analysis.py $SUBJECT_TP_PATH
	python3 $SCRIPT_PATH/report.py $SUBJECT_TP_PATH
	cd ../../	
	echo $dir processing complete!
done
