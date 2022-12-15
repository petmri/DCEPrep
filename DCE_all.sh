#!/bin/bash
# Oct 13, 2022
# FSL, AFNI, Matlab, ROCKETSHIP + parametric_scripts, ANTS, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
# control variables
EN_Z_NORM=0
EN_BIAS1=1
EN_BIAS2=0
fail=0
count=0
successes=0

# options
while getopts ":d:bBZh" options; do
	case "${options}" in
		b)
			EN_BIAS1=1
			;;
		B)	EN_BIAS2=1
			;;
		d)
			DATA_DIR=${OPTARG}
			LOG_FILE=$DATA_DIR/dce_log.txt
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, processing every folder ending in '_timepoint'."
			echo "The data must be preprocessed with `preprocess_all.sh` before running this script."
			echo "The input is `DCE_bfc_norm.nii`. The output is mainly the DCE outputs (Ktrans maps) and QC graphs."
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-Z: enable Z-slice normalization"
			echo "-d: specify main data directory containing all subject folders"
			echo "-F: fail fast, any major command failures will skip the failing timepoint"
			echo "-h: display this message"
			exit 0
			;;
		Z)
			EN_Z_NORM=1
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
cd $DATA_DIR
GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(find $HOME -name '*run_dce_auto.m' -printf '%h\n' -quit)
	SCRIPT_PATH=$(find $HOME -name '*auto_analysis.py' -printf '%h\n' -quit)
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
fi

rm dce_log.txt
for dir in */*_timepoint/; do
	date >> dce_log.txt
	echo DCE processing ${dir}...
	((count++))
	cd $dir
	SUBJECT_TP_PATH=$(pwd)

	if [ ! -f "DCE_mc_bfc_norm.nii" ]
		then
		echo Missing input file. Make sure the data has been preprocessed. Skipping $dir... >> $LOG_FILE
		continue
	fi
	
	# DCE
	# ------------------------------
	echo Begin DCE processing...
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH'); addpath '$GPUFIT_PATH/matlab'; run_dce_auto('$SUBJECT_TP_PATH/'); exit;"
	if [ ! -f "dce_patlak_fit_Ktrans.nii" ]
		then
			echo $dir "Missing Ktrans maps. DCE failed or inputs were not generated. Hopefully message below is relevant." >> $LOG_FILE
			tail -1 A_dceR1info.log >> $LOG_FILE
			fail=1
			continue
	fi
	
	# Analyze results
	# ------------------------------
	
	# Align then re-binarize gm mask
	#bad
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii segmented_t1_seg_1.nii.gz T1_gm_dyn.nii.gz
	#flirt -in segmented_t1_seg_1.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_gm_mask_dyn.nii
	#fails on 1 subject (180deg rotation)
	#flirt -in segmented_t1_seg_1.nii.gz -dof 6 -ref ref_rep.nii -o T1_gm_mask_dyn.nii
	#fslmaths T1_gm_mask_dyn.nii -thr 0.5 -bin T1_gm_mask_dyn.nii
	#good
	antsRegistrationSyN.sh -d 3 -t t -f ref_rep.nii -m segmented_t1_seg_1.nii.gz -o T1_gm_mask_dyn
	fslmaths T1_gm_mask_dynWarped.nii -thr 0.5 -bin T1_gm_mask_dyn.nii	
	
	# Align CSF mask
	#flirt -in 15_csf.nii.gz -ref ref_rep.nii -out 15_csf_mask_dyn.nii.gz -init t12dcevol.mat -applyxfm
	bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii segmented_t1_seg_0.nii.gz T1_csf_dyn.nii.gz
	#fslmaths 15_csf_mask_dyn.nii.gz -thr 20 -bin 15_csf_mask_dyn.nii
	
	# Apply masks to T1 map
	fslmaths t1_map_fixed_use_me.nii.gz -mas T1_wm_mask_dyn.nii T1_wm.nii
	fslmaths t1_map_fixed_use_me.nii.gz -mas T1_gm_mask_dyn.nii T1_gm.nii
	fslmaths t1_map_fixed_use_me.nii.gz -mas T1_csf_dyn.nii T1_csf.nii
	
	# Apply masks to Ktrans map
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_wm_mask_dyn.nii Ktrans_wm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_gm_mask_dyn.nii Ktrans_gm.nii
	fslmaths dce_patlak_fit_Ktrans.nii -mas T1_csf_dyn.nii Ktrans_csf.nii
	
	# registration QC
	high_zeros=$(python3 $SCRIPT_PATH/auto_analysis.py $SUBJECT_TP_PATH)
	if [ $high_zeros = "True" ]
		then
		# re-register
		#bash $SCRIPT_PATH/preprocess_all.sh
		echo "High % of zeros found in matter masks. May be due to poor registration. Attempting re-registration with Freesurfer..."
		bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_map_t1_fa_fit_VFA_mc.nii t1_map_fixed_use_me.nii.gz
		bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_bet_mask.nii.gz T1_bet_mask_dyn.nii.gz
		fslcpgeom 2.nii T1_bet_mask_dyn.nii.gz
		cp aif.nii aif_aligned.nii
		fslcpgeom T1_bet_mask_dyn.nii.gz aif_aligned.nii
		fslmaths aif_aligned.nii -thr 0 aif_pos.nii
		rm aif_aligned.nii
		fslmaths T1_bet_mask_dyn.nii.gz -add aif_pos.nii -thr 1 -bin T1_bet_mask_dyn_aif.nii
		fslmaths DCE_mc.nii -mas T1_bet_mask_dyn_aif.nii.gz DCE_mc_masked.nii
		
		if [ $EN_BIAS1 -eq 1 ]
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
		
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 1st_rep.nii &> /dev/null
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 5th_rep.nii &> /dev/null
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 10th_rep.nii &> /dev/null
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 20th_rep.nii &> /dev/null
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 30th_rep.nii &> /dev/null
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 40th_rep.nii &> /dev/null
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 50th_rep.nii &> /dev/null
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 60th_rep.nii &> /dev/null
		
				# Concatenation1
				3dTcat -prefix dyn_bias.nii 1st_rep_bias.nii.gz 5th_rep_bias.nii.gz 10th_rep_bias.nii.gz 20th_rep_bias.nii.gz 30th_rep_bias.nii.gz 40th_rep_bias.nii.gz 50th_rep_bias.nii.gz 60th_rep_bias.nii.gz -overwrite
		
				# Computing average across 8 bias field that have been sampled
				3dTstat -mean -prefix mean_dyn_bias_map.nii dyn_bias.nii'[0..7]' -overwrite
		
				# Normalizing motion corrected DCE image with mean bias field 
				3dcalc -a DCE_mc_masked.nii -b mean_dyn_bias_map.nii -expr a/b -prefix DCE_mc_bfc.nii -overwrite
		
				# don't forget to remove all unnecessary images 
				rm [0-9]*_rep*

		else
			#echo Motion correcting dynamic set
			#3dvolreg -heptic -verbose -base 'DCE.nii[1]' -dfile DCE_motion.txt -prefix DCE_mc_bfc.nii DCE.nii
			#3dTcat -prefix ref_rep.nii dce_mc_bfc'[1]'
			gunzip -f DCE_mc.nii.gz
			mv DCE_mc.nii DCE_mc_bfc.nii
		fi
		
		# align existing white matter mask to dynamic images and re-binarize
		#flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_wm_mask_dyn.nii
		flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -2D -o T1_wm_mask_dyn.nii
		#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_wm_mask.nii.gz T1_wm_mask_dyn.nii.gz
		#antsRegistrationSyN.sh -d 3 -t r -f ref_rep.nii -m T1_wm_mask.nii.gz -o T1_wm_mask_dyn
		#mv T1_wm_mask_dynWarped.nii.gz T1_wm_mask_dyn.nii.gz
		fslmaths T1_wm_mask_dyn.nii.gz -thr 0.3 -bin T1_wm_mask_dyn.nii.gz
		
		#fslmaths T1_wm_mask_dynWarped.nii -thr 0.7 -bin T1_wm_mask_dyn.nii
		#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_bet_mask.nii.gz T1_bet_mask_dyn.nii.gz
		#fslmaths 15_wm_mask_dyn.nii.gz -thr 1.7 -bin 15_wm_mask_dyn.nii
		#rm T1_wm_mask_dynInverseWarped.nii.gz
		#rm T1_wm_mask_dyn0GenericAffine.mat
		
		# apply wm mask to all DCE images
		fslmaths DCE_mc_bfc.nii -mas T1_wm_mask_dyn.nii.gz DCE_mc_bfc_wm.nii.gz
	
		# normalize dynamic images
		# ------------------------------
		echo Normalizing dynamic images...
		python3 $SCRIPT_PATH/DCE_norm.py $SUBJECT_TP_PATH
		if [ ! -f "DCE_mc_bfc_norm.nii" ]
			then
				echo $dir "Missing normalized DCE file." >> $LOG_FILE
				fail=1
				continue
		fi
		echo Begin DCE processing...
		matlab -nodisplay -r "cd('$ROCKETSHIP_PATH'); addpath '$GPUFIT_PATH/matlab'; run_dce_auto('$SUBJECT_TP_PATH/'); exit;"

		if [ ! -f "dce_patlak_fit_Ktrans.nii" ]
			then
				echo $dir "Missing Ktrans maps. Check terminal--DCE failed or inputs were otherwise not generated." >> $LOG_FILE
				fail=1
				continue
		fi
		
		# Analyze results
		# ------------------------------
		# Align then re-binarize gm mask
		#bad
		#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii segmented_t1_seg_1.nii.gz T1_gm_dyn.nii.gz
		#flirt -in segmented_t1_seg_1.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_gm_mask_dyn.nii
		#fails on 1 subject (180deg rotation)
		#flirt -in segmented_t1_seg_1.nii.gz -dof 6 -ref ref_rep.nii -o T1_gm_mask_dyn.nii
		#fslmaths T1_gm_mask_dyn.nii -thr 0.5 -bin T1_gm_mask_dyn.nii
		#good
		antsRegistrationSyN.sh -d 3 -t t -f ref_rep.nii -m segmented_t1_seg_1.nii.gz -o T1_gm_mask_dyn
		fslmaths T1_gm_mask_dynWarped.nii -thr 0.5 -bin T1_gm_mask_dyn.nii	
		
		# Align CSF mask
		#flirt -in 15_csf.nii.gz -ref ref_rep.nii -out 15_csf_mask_dyn.nii.gz -init t12dcevol.mat -applyxfm
		bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii segmented_t1_seg_0.nii.gz T1_csf_dyn.nii.gz
		#fslmaths 15_csf_mask_dyn.nii.gz -thr 20 -bin 15_csf_mask_dyn.nii
		
		# Apply masks to T1 map
		fslmaths t1_map_fixed_use_me.nii.gz -mas T1_wm_mask_dyn.nii T1_wm.nii
		fslmaths t1_map_fixed_use_me.nii.gz -mas T1_gm_mask_dyn.nii T1_gm.nii
		fslmaths t1_map_fixed_use_me.nii.gz -mas T1_csf_dyn.nii T1_csf.nii
		
		# Apply masks to Ktrans map
		fslmaths dce_patlak_fit_Ktrans.nii -mas T1_wm_mask_dyn.nii Ktrans_wm.nii
		fslmaths dce_patlak_fit_Ktrans.nii -mas T1_gm_mask_dyn.nii Ktrans_gm.nii
		fslmaths dce_patlak_fit_Ktrans.nii -mas T1_csf_dyn.nii Ktrans_csf.nii

		python3 $SCRIPT_PATH/auto_analysis.py $SUBJECT_TP_PATH
	fi
	
	fslmaths T1_wm_mask_dyn.nii.gz -add 2000 huh.nii
	fslmaths huh.nii.gz -thr 2001 huh.nii
	fslmaths ref_rep.nii -sub huh.nii.gz bozo.nii
	fslmaths bozo.nii -thr 0 bozo.nii
	
	fslmaths T1_gm_mask_dyn.nii.gz -add 2000 huh2.nii
	fslmaths huh2.nii.gz -thr 2001 huh2.nii
	fslmaths ref_rep.nii -sub huh2.nii.gz bozo2.nii
	fslmaths bozo2.nii -thr 0 bozo2.nii
	
	python3 $SCRIPT_PATH/report.py $SUBJECT_TP_PATH
	cd ../../
	echo $dir processing complete! >> $LOG_FILE
	((successes++))
done

((failures=count-successes))
echo "Completed DCE processing for $count subjects." >> $LOG_FILE
echo $successes subjects succeeded >> $LOG_FILE
echo $failures subjects failed >> $LOG_FILE

if [ $fail -eq 1 ]
	then
	exit 1
fi
