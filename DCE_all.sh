#!/bin/bash
# Oct 13, 2022
# FSL, AFNI, Matlab, ROCKETSHIP + parametric_scripts, ANTS, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
# control variables
COMPARISON_MODE=0
EN_BIAS1=0
fail=0
count=0
successes=0
USE_FREESURFER=0
SKIP_IF_SUCCESS=0
PURGE_INTERMEDIATES=1
GIGA_PURGE=0
shopt -s extglob

# options
while getopts ":d:bC::fhs" options; do
	case "${options}" in
		b)
			EN_BIAS1=1
			;;
		C)
			COMPARISON_MODE=1
			OUTPUT_DIR=${OPTARG}
			;;
		d)
			DATA_DIR=${OPTARG}
			if [ ${DATA_DIR::-1} == "/" ]
				then
				DATA_DIR=${DATA_DIR::-1}
			fi
			date=$(date +%Y-%m-%d)
			LOG_FILE=$DATA_DIR/dce_log_$date.txt
			;;
		f)
			USE_FREESURFER=1
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, processing every folder ending in '_timepoint'."
			echo "The data must be preprocessed with \`preprocess_all.sh\` before running this script."
			echo "The input is \`DCE_bfc_norm.nii\`. The output is mainly the DCE outputs (Ktrans maps) and QC graphs."
			echo "-b: enable first round of bias field corrections"
			echo "-C: enable comparison mode. Specify output directory."
			echo "-d: specify main data directory containing all subject folders"
			echo "-h: display this message"
			exit 0
			;;
		s)
			SKIP_IF_SUCCESS=1
			;;
		*)
			echo "Invalid option ${OPTARG}. Please use -h for a list of valid options."
			exit 1
			;;
	esac
done

if [ -z "$DATA_DIR" ]
	then
		echo "ERROR: Please use '-d [dir_path]' to pass the path to your main data directory to this script."
		exit 1
fi
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(find $HOME -name '*run_dce_auto.m' -printf '%h\n' -quit || find / -name '*run_dce_auto.m' -printf '%h\n' -quit) &> /dev/null
	SCRIPT_PATH=$(dirname "$(realpath $0)")
	GPUFIT_PATH=$(find $HOME -name 'GpufitConstrainedMex.mexa64' -printf '%h\n' -quit || find / -name 'GpufitConstrainedMex.mexa64' -printf '%h\n' -quit)
	GPUFIT_M_PATH=$(find $HOME -name 'ModelID.m' -printf '%h\n' -quit || find / -name 'ModelID.m' -printf '%h\n' -quit)
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
	GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
fi
cd $DATA_DIR || exit 1

# rm dce_log.txt
for dir in */*_timepoint/; do
	dir=$DATA_DIR/${dir::-1}
	date >> dce_log.txt
	echo "DCE processing ${dir}..."
	((count++))
	cd $dir || exit 1
	if [ $COMPARISON_MODE -eq 1 ]
		then
		cd "$OUTPUT_DIR" || exit 1
	fi
	SUBJECT_TP_PATH=$(pwd)

	if [ $SKIP_IF_SUCCESS -eq 1 ]
		then
		if [ -f "case_report.html" ]
			then
			echo "Skipping $dir because it has already been processed." >> $LOG_FILE
			cd $DATA_DIR
			continue
		fi
	fi
	if [ ! -f "DCE_mc_bfc_norm.nii.gz" ]
		then
		echo Missing input file. Make sure the data has been preprocessed. Skipping $dir... >> $LOG_FILE
		cd $DATA_DIR
		fail=1
		continue
	fi
	
	# DCE
	# ------------------------------
	echo Begin DCE processing...
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH'); addpath '$GPUFIT_PATH'; addpath '$GPUFIT_M_PATH'; run_dce_auto('$SUBJECT_TP_PATH/'); exit;"
	# gzip -f dcedynamicCt.nii
	if [ ! -f "dce_patlak_fit_Ktrans.nii" ]
		then
			echo $dir "Missing Ktrans maps. DCE failed or inputs were not generated. Hopefully message below is relevant." >> $LOG_FILE
			tail -1 A_dceR1info.log >> $LOG_FILE
			cd $DATA_DIR
			fail=1
			continue
	fi
	
	# Analyze results
	# ------------------------------
	
	# Align then re-binarize gm mask
	# antsRegistrationSyN.sh -d 3 -t t -f ref_rep.nii -m segmented_t1_seg_1.nii.gz -o T1_gm_mask_dyn
	antsApplyTransforms -i segmented_t1_seg_1.nii.gz -r ref_rep.nii -t T1_dyn0GenericAffine.mat -o T1_gm_mask_dyn_pv.nii &> /dev/null
	fslmaths T1_gm_mask_dyn_pv.nii -thr 0.9 -bin T1_gm_mask.nii
	rm T1_gm_mask_dyn_pv.nii
	
	# Align CSF mask
	#flirt -in 15_csf.nii.gz -ref ref_rep.nii -out 15_csf_mask_dyn.nii.gz -init t12dcevol.mat -applyxfm
	antsApplyTransforms -i segmented_t1_seg_0.nii.gz -r ref_rep.nii -t T1_dyn0GenericAffine.mat -o T1_csf_mask_dyn_pv.nii &> /dev/null
	fslmaths T1_csf_mask_dyn_pv.nii -thr 0.9 -bin T1_csf_mask.nii
	rm T1_csf_mask_dyn_pv.nii

	#fslmaths 15_csf_mask_dyn.nii.gz -thr 20 -bin 15_csf_mask_dyn.nii
	
	# Apply masks to T1 map
	fslmaths T1_map_t1_fa_fit_VFA.nii -mas T1_wm_mask.nii T1_wm.nii
	fslmaths T1_map_t1_fa_fit_VFA.nii -mas T1_gm_mask.nii T1_gm.nii
	fslmaths T1_map_t1_fa_fit_VFA.nii -mas T1_csf_mask.nii T1_csf.nii
	
	# Apply masks to Ktrans map
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_wm_mask.nii Ktrans_wm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_gm_mask.nii Ktrans_gm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_csf_mask.nii Ktrans_csf.nii
	
	# registration QC
	python3 $SCRIPT_PATH/auto_analysis.py $SUBJECT_TP_PATH
	
	fslmaths T1_wm_mask.nii.gz -add 2000 huh.nii
	fslmaths huh.nii.gz -thr 2001 huh.nii
	fslmaths ref_rep.nii -sub huh.nii.gz bozo.nii
	fslmaths bozo.nii -thr 0 bozo.nii
	
	fslmaths T1_gm_mask.nii.gz -add 2000 huh2.nii
	fslmaths huh2.nii.gz -thr 2001 huh2.nii
	fslmaths ref_rep.nii -sub huh2.nii.gz bozo2.nii
	fslmaths bozo2.nii -thr 0 bozo2.nii
	
	flirt -in DCE_mc.nii.gz -ref $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz -omat DCE2MNI.mat -out DCE_MNI_FSL.nii.gz
	flirt -in $dir/T1.nii -ref $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz -out t1w_MNI.nii.gz -bins 256 -cost mutualinfo -searchrx -90 90 -searchry -90 90 -searchrz -90 90 -dof 12 -interp trilinear
	flirt -in dce_patlak_fit_Ktrans.nii -ref $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz -out ktrans_2_MNI.nii.gz -init DCE2MNI.mat -applyxfm
	python3 $SCRIPT_PATH/ktrans_report.py $SUBJECT_TP_PATH
	python3 $SCRIPT_PATH/case_report.py $dir $SUBJECT_TP_PATH
	if [ $PURGE_INTERMEDIATES -eq 1 ] && [ $COMPARISON_MODE -eq 1 ]
		then
		rm -f !(Ktrans_*|T1_gm*|T1_wm*|T1_csf*|*_patlak_fit*.nii|case_report.html|*_MNI.nii.gz|*fit_VFA.nii|figures|dce*.png)
	elif [ $GIGA_PURGE -eq 1 ]
		then
		rm -f !(case_report.html|figures)
	fi
	cd $DATA_DIR
	echo $dir processing complete! >> $LOG_FILE
	((successes++))
done

python3 $SCRIPT_PATH/population_report.py $DATA_DIR $OUTPUT_DIR
((failures=count-successes))
echo "Completed DCE processing for $count subjects." >> $LOG_FILE
echo $successes subjects succeeded >> $LOG_FILE
echo $failures subjects failed >> $LOG_FILE

if [ $fail -eq 1 ]
	then
	exit 1
fi
