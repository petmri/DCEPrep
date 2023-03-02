#!/bin/bash
shopt -s extglob
# FSL, Matlab, ROCKETSHIP + parametric_scripts, ANTS, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
# variables
EN_Z_NORM=0
EN_BIAS1=0
EN_BIAS2=0
#EN_MOTION_CORR=1
USE_FREESURFER=0

# internal vars (don't change)
fail=0
failures=0
clean=0
count=0
current=0
ETA=0
mETA=0
prog=0
successes=0

# options
while getopts ":d:bBZfhc" options; do
	case "${options}" in
		b)
			EN_BIAS1=1
			;;
		B)	EN_BIAS2=1
			;;
		c)
			clean=1
			;;
		d)
			DATA_DIR=${OPTARG}
			LOG_FILE=$DATA_DIR/preprocessing_log.txt
			;;
		f)
			USE_FREESURFER=1
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, preprocessing every folder ending in '_timepoint'."
			echo "The output is the DCE input, which are the corrected dynamic images, brain mask, T1 maps."
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-c: clean generated files prior to processing"
			echo "-Z: enable Z-slice normalization"
			echo "-d: specify main data directory containing all subject folders"
			echo "-f: use freesurfer for registration (seems to cut off top of cortical region for most subjects, works perfectly for one site)"
			echo "-h: display this message"
			exit 0
			;;
		Z)
			EN_Z_NORM=1
			;;
		*)
			echo "Invalid flag ${OPTARG}. Please use -h for a list of valid flags."
			exit 1
			;;
	esac
done

if [ -z "$DATA_DIR" ]
	then
		echo "ERROR: Please use '-d [dir_path]' to pass the path to your main data directory to this script."
		exit 1
fi
cd $DATA_DIR || exit 1
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(find $HOME -name '*run_dce_auto.m' -printf '%h\n' -quit || find / -name '*run_dce_auto.m' -printf '%h\n' -quit) &> /dev/null
	SCRIPT_PATH=$(find $HOME -name '*auto_analysis.py' -printf '%h\n' -quit || find / -name '*auto_analysis.py' -printf '%h\n' -quit) &> /dev/null
	GPUFIT_PATH=$(find $HOME -name 'gpufit_constrained.m' -printf '%h\n' -quit || find / -name 'gpufit_constrained.m' -printf '%h\n' -quit) &> /dev/null
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
	GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
fi

# count timepoints
for dir in */*_timepoint/; do
	((count++))
done
# Run bias correction on VFA data 
# ------------------------------
rm preprocessing_log.txt
for dir in */*_timepoint/; do
	date >> preprocessing_log.txt
	echo "Preprocessing ${dir}..."
	((current++))
	cd $dir || exit
	SUBJECT_TP_PATH=$(pwd)

	if [ ! -f "2.nii" ] || [ ! -f "5.nii" ] || [ ! -f "10.nii" ] || [ ! -f "12.nii" ] || [ ! -f "15.nii" ] || [ ! -f "DCE.nii" ] || [ ! -f "T1.nii" ]
		then
		echo "$dir Base file(s) missing! Expected VFAs 2.nii, 5.nii, 10.nii, 12.nii, 15.nii, DCE.nii, and T1.nii (MP-RAGE). Skipping timepoint..." >> $LOG_FILE
		continue
	fi
	
	if [ $clean -eq 1 ]
		then
		echo Cleaning folder...
        rm -f !(2.nii|5.nii|10.nii|12.nii|15.nii|DCE.nii|aif.nii|T1.nii|*.json)
    fi
	
	# HD-BET brain extraction & segmentations from MP-RAGE
	SECONDS=0
	echo -ne "HD-BET MP-RAGE [                                                  ] $prog% ($current/$count) Calculating runtime...   \r"
	
	if [ nvidia-smi ]
		then
		# about 15 min
		hd-bet -i T1.nii &> /dev/null
		mETA=$(echo "scale=0;  $SECONDS * 34 * ($count - $current + 1) / 60" | bc -l)
	else
		# 2-3 hours
		hd-bet -i T1.nii -device cpu &> /dev/null
		mETA=$(echo "scale=0;  $SECONDS * 2 * ($count - $current + 1) / 60" | bc -l)
	fi
	prog=$(echo "scale=2;  $prog + 3.33 / $count" | bc -l)

	echo -ne "T1 SEG w/ FAST [=>                                                ] $prog% ($current/$count) ~$mETA min remaining \r"
	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -g -o segmented_t1 T1_bet.nii.gz &> /dev/null
	ETA=$(echo "scale=0;  $mETA - ($SECONDS/60)" | bc -l)
	#ETA=$(echo "scale=0;  $mETA - $mETA * .0667" | bc -l)
	prog=$(echo "scale=2;  $prog + 6.67 / $count" | bc -l)
	echo -ne "BFC FAST VFA2  [====>                                             ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	bash $SCRIPT_PATH/tktregistration.sh 2.nii segmented_t1_seg_2.nii.gz T1_wm_mask.nii.gz &> /dev/null
	fslmaths T1_wm_mask.nii.gz -thr 0.4 -bin T1_wm_mask.nii.gz &> /dev/null
	# FAST documentation recommends brain masking first
	#fslmaths 2.nii -mas T1_bet_mask.nii.gz 2_masked.nii 
	#fslmaths 5.nii -mas T1_bet_mask.nii.gz 5_masked.nii
	#fslmaths 10.nii -mas T1_bet_mask.nii.gz 10_masked.nii
	#fslmaths 12.nii -mas T1_bet_mask.nii.gz 12_masked.nii
	#fslmaths 15.nii -mas T1_bet_mask.nii.gz 15_masked.nii
	cp 2.nii 2_masked.nii
	cp 5.nii 5_masked.nii
	cp 10.nii 10_masked.nii
	cp 12.nii 12_masked.nii
	cp 15.nii 15_masked.nii
	gzip -f *_masked.nii
	
	if [ $EN_BIAS1 -eq 1 ]
		then
		if [ ! -f "15_bfc.nii" ]
		then
			#echo "Bias field correction with FAST"
			# don't forget to remove all unnecessary images
			fast -t 3 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o 2_masked.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "BFC FAST VFA5  [=======>                                          ] $prog% ($current/$count) ~$ETA min remaining \r"
			mv 2_masked_restore* 2_bfc.nii.gz

			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o 5_masked.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "BFC FAST VFA10 [==========>                                       ] $prog% ($current/$count) ~$ETA min remaining \r"
			mv 5_masked_restore* 5_bfc.nii.gz

			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o 10_masked.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "BFC FAST VFA12 [=============>                                    ] $prog% ($current/$count) ~$ETA min remaining \r"
			mv 10_masked_restore* 10_bfc.nii.gz

			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o 12_masked.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "BFC FAST VFA15 [================>                                 ] $prog% ($current/$count) ~$ETA min remaining \r"
			mv 12_masked_restore* 12_bfc.nii.gz

			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o 15_masked.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "VFA POLY NORM  [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"
			mv 15_masked_restore* 15_bfc.nii.gz
			
			rm [0-9]*_masked_[mps]*
		else
			echo Found BFC VFAs. Skipping BFC...
		fi

		# apply wm mask to all VFAs
		fslmaths 2_bfc.nii.gz -mas T1_wm_mask.nii.gz 2_bfc_wm.nii.gz &> /dev/null
		fslmaths 5_bfc.nii.gz -mas T1_wm_mask.nii.gz 5_bfc_wm.nii.gz &> /dev/null
		fslmaths 10_bfc.nii -mas T1_wm_mask.nii.gz 10_bfc_wm.nii.gz &> /dev/null
		fslmaths 12_bfc.nii -mas T1_wm_mask.nii.gz 12_bfc_wm.nii.gz &> /dev/null
		fslmaths 15_bfc.nii -mas T1_wm_mask.nii.gz 15_bfc_wm.nii.gz &> /dev/null
	else
		# dumb file name management for norm only runs
		fslmaths 2.nii -mas T1_bet_mask.nii.gz 2_bfc.nii &> /dev/null
		fslmaths 5.nii -mas T1_bet_mask.nii.gz 5_bfc.nii &> /dev/null
		fslmaths 10.nii -mas T1_bet_mask.nii.gz 10_bfc.nii &> /dev/null
		fslmaths 12.nii -mas T1_bet_mask.nii.gz 12_bfc.nii &> /dev/null
		fslmaths 15.nii -mas T1_bet_mask.nii.gz 15_bfc.nii &> /dev/null
		
		echo "Skipping BFC... but still segmenting one VFA for matter masks"
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 15_bfc.nii &> /dev/null
		rm 15_bfc_mixeltype.nii.gz &> /dev/null
		rm 15_bfc_pve_0.nii.gz &> /dev/null
		rm 15_bfc_pve_1.nii.gz &> /dev/null
		rm 15_bfc_pve_2.nii.gz &> /dev/null
		rm 15_bfc_pveseg.nii.gz &> /dev/null
		rm 15_bfc_seg.nii.gz &> /dev/null
		
		# threshold and binarize wm mask
		#fslmaths 15_bfc_seg.nii.gz -thr 3 -uthr 3 15_wm.nii
		
		# apply wm mask to all VFAs
		fslmaths 2_bfc.nii -mas T1_wm_mask.nii.gz 2_bfc_wm.nii &> /dev/null
		fslmaths 5_bfc.nii -mas T1_wm_mask.nii.gz 5_bfc_wm.nii &> /dev/null
		fslmaths 10_bfc.nii -mas T1_wm_mask.nii.gz 10_bfc_wm.nii &> /dev/null
		fslmaths 12_bfc.nii -mas T1_wm_mask.nii.gz 12_bfc_wm.nii &> /dev/null
		fslmaths 15_bfc.nii -mas T1_wm_mask.nii.gz 15_bfc_wm.nii &> /dev/null
		
		# apply MP-RAGE wm mask
		fslmaths 2_bfc.nii -mas T1_wm_mask.nii.gz 2_bfc_wm.nii &> /dev/null
		fslmaths 5_bfc.nii -mas T1_wm_mask.nii.gz 5_bfc_wm.nii &> /dev/null
		fslmaths 10_bfc.nii -mas T1_wm_mask.nii.gz 10_bfc_wm.nii &> /dev/null
		fslmaths 12_bfc.nii -mas T1_wm_mask.nii.gz 12_bfc_wm.nii &> /dev/null
		fslmaths 15_bfc.nii -mas T1_wm_mask.nii.gz 15_bfc_wm.nii &> /dev/null
	fi

	# Run Z-axis normalization VFA data
	# ------------------------------
	if [ $EN_Z_NORM -eq 1 ] 
		then
		#echo begin slice normalization
		python3 $SCRIPT_PATH/VFA_norm.py $SUBJECT_TP_PATH &> /dev/null
		prog=$(echo "scale=2;  $prog + .33 / $count" | bc -l)
		echo -ne "VFA MOTIONCORR [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"
	fi

	if [ ! -f "15_BFC_Z.nii" ]
		then
			echo $dir "Missing Z-normalized files. Z-norm likely failed due to non-existent inputs." >> $LOG_FILE
			fail=1
			continue
	fi

	if [ $EN_BIAS2 -eq 1 ]
		then
		# 2nd Bias correction VFA data
		# ------------------------------
		echo Begin second round of BFC
		# Bias field correction with FAST
		# don't forget to remove all unnecessary images
		fast -t 3 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 2_BFC_Z.nii
		fslmaths 2_BFC_Z.nii -div 2_BFC_Z_bias.nii.gz 2_b2corr.nii
		
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 5_BFC_Z.nii
		fslmaths 5_BFC_Z.nii -div 5_BFC_Z_bias.nii.gz 5_b2corr.nii

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 10_BFC_Z.nii
		fslmaths 10_BFC_Z.nii -div 2_BFC_Z_bias.nii.gz 10_b2corr.nii

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 12_BFC_Z.nii
		fslmaths 12_BFC_Z.nii -div 2_BFC_Z_bias.nii.gz 12_b2corr.nii

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 15_BFC_Z.nii
		fslmaths 15_BFC_Z.nii -div 2_BFC_Z_bias.nii.gz 15_b2corr.nii

		# concatenates 5 images in one VFA.nii.gz image  
		fslmerge -t VFA.nii.gz 2_b2corr.nii 5_b2corr.nii 10_b2corr.nii 12_b2corr.nii 15_b2corr.nii
		
		rm [0-9]*_BFC_Z_*
		
	elif [ $EN_Z_NORM -eq 1 ] 
		then
		#echo Concatenating Z-norm\'d images
		# concatenates 5 images in one VFA.nii.gz image
		fslmerge -t VFA.nii.gz 2_BFC_Z.nii 5_BFC_Z.nii 10_BFC_Z.nii 12_BFC_Z.nii 15_BFC_Z.nii &> /dev/null

	elif [ $EN_BIAS1 -eq 1 ]
		then
		echo Concatenating non Z\'d images
		fslmerge -t VFA.nii 2_bfc.nii 5_bfc.nii 10_bfc.nii 12_bfc.nii 15_bfc.nii &> /dev/null
	else
		echo Concatenating raw images
		fslmerge -t VFA.nii 2_masked.nii 5_masked.nii 10_masked.nii 12_masked.nii 15_masked.nii &> /dev/null
	fi
	
	if [ ! -f "VFA.nii.gz" ]
		then
			echo "$dir missing VFA file. Component files may have failed." >> $LOG_FILE
			fail=1
			continue
	fi
	
	# motion correction of VFA
	# ------------------------------
	mcflirt -in VFA.nii.gz -refvol 'VFA.nii.gz[0]' -cost mutualinfo -report -verbose -plots -o VFA_mc.nii &> /dev/null
	prog=$(echo "scale=2;  $prog + .5 / $count" | bc -l)
	echo -ne "MAKE T1 MAPS   [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"
	gunzip -f VFA_mc.nii.gz
	
	if [ ! -f "VFA_mc.nii" ]
		then
			echo $dir "Missing VFA_mc file. Motion correction may have failed." >> $LOG_FILE
			fail=1
			continue
	fi

	# T1 mapping where the input image is 'VFA.motioncorrected.nii'
	# ------------------------------
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH/parametric_scripts/custom_scripts'); addpath '$ROCKETSHIP_PATH'; addpath '$ROCKETSHIP_PATH/dce'; addpath '$ROCKETSHIP_PATH/external_programs'; addpath '$ROCKETSHIP_PATH/external_programs/niftitools'; addpath '$ROCKETSHIP_PATH/parametric_scripts'; addpath '$GPUFIT_PATH'; T1mapping_fit('$SUBJECT_TP_PATH/'); exit;" &> /dev/null
	((diff = SECONDS - diff))
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + 1.33 / $count" | bc -l)
	echo -ne "DCE MOTIONCORR [====================>                             ] $prog% ($current/$count) ~$ETA min remaining \r"
	if [ ! -f "T1_map_t1_fa_fit_VFA_mc.nii" ]
		then
			echo $dir "Missing T1 map file. T1 mapping may have failed." >> $LOG_FILE
			fail=1
			continue
	fi
	
	# Motion correction of dynamic images using FSL
	# ------------------------------
	#echo Motion correcting dynamic images...
	mcflirt -in DCE.nii -refvol 'DCE.nii[1]' -cost mutualinfo -report -plots -o DCE_mc.nii &> /dev/null
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
	echo -ne "REG T1 MAP->DCE[=======================>                          ] $prog% ($current/$count) ~$ETA min remaining \r"
	max=$(python3 $SCRIPT_PATH/max_disp.py $SUBJECT_TP_PATH)
	echo -e "\e[1;33m$max\e[0m" >> $LOG_FILE
	if [ ! -f "DCE_mc.nii.gz" ]
		then
			echo $dir "Missing motion corrected DCE file." >> $LOG_FILE
			fail=1
			continue
	fi
	
	# Align T1 map with Dynamic data
	# ------------------------------
	fslmerge -n 1 ref_rep.nii DCE_mc.nii &> /dev/null
	gunzip -f ref_rep.nii.gz
	# FRAUDSURFER doesn't really do anything for most subjects
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_map_t1_fa_fit_VFA_mc.nii t1_map_fixed_use_me.nii.gz
	antsRegistrationSyN.sh -d 3 -t t -f ref_rep.nii -m T1_map_t1_fa_fit_VFA_mc.nii -o t1_map_fixed_use_me &> /dev/null
	mv t1_map_fixed_use_meWarped.nii.gz t1_map_fixed_use_me.nii.gz
	rm t1_map_fixed_use_meInverseWarped.nii.gz
	rm t1_map_fixed_use_me0GenericAffine.mat
	#prog=$(echo "scale=2;  $prog + .55 / $count" | bc -l)
	#echo -ne "ANTSREG T1->DCE[=======================>                          ] $prog% ($current/$count) ~$ETA min remaining \r"
	if [ ! -f "t1_map_fixed_use_me.nii.gz" ]
		then
			echo "Missing registered T1 map." >> $LOG_FILE
			fail=1
			continue
	fi
	
	# align and apply brain mask
	#flirt -in T1.nii -ref ref_rep.nii -dof 12 -omat T1toDCE.mat -o T1_dyn.nii
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1.nii T1_dyn.nii.gz
	#antsRegistrationSyN.sh -d 3 -t a -f ref_rep.nii -m T1.nii -o T1_dyn &> /dev/null
	#mv T1_dynWarped.nii.gz T1_dyn.nii.gz
	#rm T1_dyn0GenericAffine.mat
	#rm T1_dynInverseWarped.nii.gz
	prog=$(echo "scale=2;  $prog + 2.77 / $count" | bc -l)
	echo -ne "REG BET MASK   [========================>                         ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	#flirt -in T1_bet_mask.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_bet_mask_dyn.nii
	#flirt -in T1_bet_mask.nii.gz -ref ref_rep.nii -dof 6 -o T1_bet_mask_dyn.nii
	#fslmaths T1_bet_mask_dyn.nii -bin T1_bet_mask_dyn.nii
	if [ $USE_FREESURFER -eq 1 ]
		then
		echo "Registering brain mask to dynamic space with Freesurfer..."
		bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_bet_mask.nii.gz T1_bet_mask_dyn.nii.gz
	else
		#echo "Registering brain mask to dynamic space with ANTs..."
		antsRegistrationSyN.sh -d 3 -t t -f ref_rep.nii -m T1_bet_mask.nii.gz -o T1_bet_mask_dyn &> /dev/null
		mv T1_bet_mask_dynWarped.nii.gz T1_bet_mask_dyn.nii.gz
		rm T1_bet_mask_dynInverseWarped.nii.gz
		rm T1_bet_mask_dyn0GenericAffine.mat
		fslmaths T1_bet_mask_dyn.nii.gz -thr 1 -bin T1_bet_mask_dyn.nii.gz &> /dev/null
		prog=$(echo "scale=2;  $prog + 0.55 / $count" | bc -l)
		ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
		echo -ne "FAST DCE REP 1 [========================>                         ] $prog% ($current/$count) ~$ETA min remaining \r"
	fi
	
	# ensure AIF is included in mask
	fslcpgeom 2.nii T1_bet_mask_dyn.nii.gz
	cp aif.nii aif_aligned.nii
	fslcpgeom T1_bet_mask_dyn.nii.gz aif_aligned.nii
	fslmaths aif_aligned.nii -thr 0 aif_pos.nii &> /dev/null
	rm aif_aligned.nii
	fslmaths T1_bet_mask_dyn.nii.gz -add aif_pos.nii -thr 1 -bin T1_bet_mask_dyn_aif.nii &> /dev/null
	fslmaths DCE_mc.nii -mas T1_bet_mask_dyn_aif.nii.gz DCE_mc_masked.nii &> /dev/null
		
	if [ $EN_BIAS1 -eq 1 ]
		then
		if [ ! -f "DCE_mc_bfc.nii" ]
			then
			# Applying bias field correction on dynamic images
			# ------------------------------
			#echo Applying BFC to dynamic images...
			fslmerge -n 0 1st_rep.nii DCE_mc_masked.nii		# extract images from different DCE repetitions
			fslmerge -n 4 5th_rep.nii DCE_mc_masked.nii
			fslmerge -n 9 10th_rep.nii DCE_mc_masked.nii
			fslmerge -n 19 20th_rep.nii DCE_mc_masked.nii
			fslmerge -n 29 30th_rep.nii DCE_mc_masked.nii
			fslmerge -n 39 40th_rep.nii DCE_mc_masked.nii
			fslmerge -n 49 50th_rep.nii DCE_mc_masked.nii
			fslmerge -n 59 60th_rep.nii DCE_mc_masked.nii


			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 1st_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE REP 5 [===========================>                      ] $prog% ($current/$count) ~$ETA min remaining \r"
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 5th_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE REP 10[==============================>                   ] $prog% ($current/$count) ~$ETA min remaining \r"
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 10th_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE REP 20[=================================>                ] $prog% ($current/$count) ~$ETA min remaining \r"
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 20th_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE REP 30[====================================>             ] $prog% ($current/$count) ~$ETA min remaining \r"
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 30th_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE REP 40[=======================================>          ] $prog% ($current/$count) ~$ETA min remaining \r"
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 40th_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE REP 50[==========================================>       ] $prog% ($current/$count) ~$ETA min remaining \r"
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 50th_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE REP 60[=============================================>    ] $prog% ($current/$count) ~$ETA min remaining \r"
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 60th_rep.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "DCE BFC + NORM [================================================> ] $prog% ($current/$count) ~$ETA min remaining \r"

			# Concatenation1
			fslmerge -t dyn_bias.nii.gz *_rep_bias.nii.gz
	
			# Computing average across 8 bias field that have been sampled
			fslmaths dyn_bias.nii.gz -Tmean mean_dyn_bias_map.nii.gz
	
			# Normalizing motion corrected DCE image with mean bias field 
			fslmaths DCE_mc_masked.nii.gz -div mean_dyn_bias_map.nii.gz DCE_mc_bfc.nii
	
			# remove sampled slice files
			rm [0-9]*_rep*
		else
			echo Skipping DCE BFC because it already exists...
		fi
	else
		#echo Motion correcting dynamic set
		gunzip -f DCE_mc.nii.gz
		mv DCE_mc.nii DCE_mc_bfc.nii
	fi
	
	# align existing white matter mask to dynamic images and re-binarize
	#flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_wm_mask_dyn.nii
	flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -2D -o T1_wm_mask_dyn.nii &> /dev/null
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_wm_mask.nii.gz T1_wm_mask_dyn.nii.gz
	#antsRegistrationSyN.sh -d 3 -t r -f ref_rep.nii -m T1_wm_mask.nii.gz -o T1_wm_mask_dyn
	#mv T1_wm_mask_dynWarped.nii.gz T1_wm_mask_dyn.nii.gz
	fslmaths T1_wm_mask_dyn.nii.gz -thr 0.3 -bin T1_wm_mask_dyn.nii.gz &> /dev/null
	
	#fslmaths T1_wm_mask_dynWarped.nii -thr 0.7 -bin T1_wm_mask_dyn.nii
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_bet_mask.nii.gz T1_bet_mask_dyn.nii.gz
	#fslmaths 15_wm_mask_dyn.nii.gz -thr 1.7 -bin 15_wm_mask_dyn.nii
	#rm T1_wm_mask_dynInverseWarped.nii.gz
	#rm T1_wm_mask_dyn0GenericAffine.mat
	
	# apply wm mask to all DCE images
	fslmaths DCE_mc_bfc.nii -mas T1_wm_mask_dyn.nii.gz DCE_mc_bfc_wm.nii.gz &> /dev/null

	# normalize dynamic images
	# ------------------------------
	#echo Normalizing dynamic images...
	python3 $SCRIPT_PATH/DCE_norm.py $SUBJECT_TP_PATH &> /dev/null

	if [ ! -f "DCE_mc_bfc_norm.nii" ]
		then
			echo $dir "Missing normalized DCE file." >> $LOG_FILE
			fail=1
			continue
	fi

	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + .6 / $count" | bc -l)
	echo -ne "SUBJ COMPLETED [==================================================] $prog% ($current/$count) ~$ETA min remaining \r"

	cd ../../
	echo $dir preprocessing complete! >> $LOG_FILE
	let successes++
done

	prog=$(echo "scale=2;  100.00" | bc -l)
	echo -ne "PREP COMPLETED [==================================================] $prog% ($current/$count)\r"

((failures=count-successes))
echo Completed preprocessing for $count subjects. >> $LOG_FILE
echo $successes subjects succeeded >> $LOG_FILE
echo $failures subjects failed >> $LOG_FILE

if [ $fail -eq 1 ]
	then
	exit 1
fi
