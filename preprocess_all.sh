#!/bin/bash
shopt -s extglob
# FSL, Matlab, ROCKETSHIP + parametric_scripts, ANTS, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
# variables
EN_Z_NORM=0
EN_BIAS1=0
EN_BIAS2=0
EN_MOTION_CORR=0
T1_ONLY=0
USE_FREESURFER=0
USE_AUTO_AIF=0
SKIP_IF_SUCCESS=0

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
while getopts ":d:bBAZfhcmst" options; do
	case "${options}" in
		A)
			USE_AUTO_AIF=1
			;;
		b)
			EN_BIAS1=1
			;;
		B)	
			EN_BIAS2=1
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
			echo "-A: enable AutoAIF"
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-c: clean generated files prior to processing"
			echo "-d: specify main data directory containing all subject folders"
			echo "-f: use freesurfer for registration (seems to cut off top of cortical region for most subjects, works perfectly for one site)"
			echo "-h: display this message"
			echo "-m: enable motion correction"
			echo "-s: skip processing if DCE input file already exists"
			echo "-t: only run up to T1 mapping"
			echo "-Z: enable Z-slice normalization"
			exit 0
			;;
		m)
			EN_MOTION_CORR=1
			;;
		s)
			SKIP_IF_SUCCESS=1
			;;
		t)
			T1_ONLY=1
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

if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(find $HOME -name '*run_dce_auto.m' -printf '%h\n' -quit || find / -name '*run_dce_auto.m' -printf '%h\n' -quit) &> /dev/null
	SCRIPT_PATH=$(dirname "$(realpath $0)")
	GPUFIT_PATH=$(find $HOME -name 'GpufitCudaAvailableMex.mexa64' -printf '%h\n' -quit || find / -name 'GpufitCudaAvailableMex.mexa64' -printf '%h\n' -quit) &> /dev/null
	GPUFIT_M_PATH=$(find $HOME -name 'ModelID.m' -printf '%h\n' -quit || find / -name 'ModelID.m' -printf '%h\n' -quit)
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
	GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
fi
echo "SCRIPT_PATH: $SCRIPT_PATH"
cd $DATA_DIR || exit 1
# count timepoints
for dir in */*_timepoint/; do
	((count++))
done
# Run bias correction on VFA data 
# ------------------------------
rm -f preprocessing_log.txt
for dir in */*_timepoint/; do
	date >> preprocessing_log.txt
	echo "Preprocessing ${dir}..."
	((current++))
	cd $dir || exit 1
	SUBJECT_TP_PATH=$(pwd)

	if [ $SKIP_IF_SUCCESS -eq 1 ]
		then
		if [ -f "DCE_mc_bfc_norm.nii" ]
			then
			echo "Skipping ${dir} because it has already been processed." >> $LOG_FILE
			cd ../..
			continue
		fi
	fi

	# get list of VFAs
	VFA_LIST=($(ls -1 *.nii | grep -v "DCE.nii" | grep -v "T1.nii" | grep -v "aif.nii"))
	# sort VFAs
	VFA_LIST=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o -E '[0-9]+.nii'| sort -n))
	echo "Found ${#VFA_LIST[@]} VFAs: ${VFA_LIST[@]}"
	VFA_NUMS=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o '[0-9]*'))
	# error if no VFAs found
	if [ ${#VFA_LIST[@]} -eq 0 ]
		then
		echo "$dir No VFAs found! Skipping timepoint..." >> $LOG_FILE
		cd ../..
		continue
	fi

	if [ ! -f "2.nii" ] || [ ! -f "5.nii" ] || [ ! -f "10.nii" ] || [ ! -f "12.nii" ] || [ ! -f "15.nii" ] || [ ! -f "DCE.nii" ] || [ ! -f "T1.nii" ]
		then
		echo "$dir Base file(s) missing! Expected VFAs 2.nii, 5.nii, 10.nii, 12.nii, 15.nii, DCE.nii, and T1.nii (MP-RAGE). Skipping timepoint..." >> $LOG_FILE
		cd ../..
		continue
	fi
	
	if [ $clean -eq 1 ]
		then
		echo Cleaning folder...
        # rm -f !(2.nii|5.nii|10.nii|12.nii|15.nii|DCE.nii|aif.nii|T1.nii|*.json)
		# remove all files except for the VFA list, DCE, AIF, T1, and json files
		rm -dfr !([0-9]*.nii|DCE.nii|aif.nii|T1.nii|*.json)
		rm *BFC*
    fi
	
	# HD-BET brain extraction & segmentations from MP-RAGE
	SECONDS=0
	echo -ne "HD-BET MP-RAGE [                                                  ] $prog% ($current/$count) Calculating runtime...   \r"
	
	if [ ! -f "T1_bet_mask.nii.gz" ]
		then
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
	fi
	prog=$(echo "scale=2;  $prog + 3.33 / $count" | bc -l)

	# register everything to dynamic space
	# Motion correction of dynamic images using FSL
	# ------------------------------
	#echo Motion correcting dynamic images...
	if [ $EN_MOTION_CORR -eq 1 ]
		then
		mcflirt -in DCE.nii -refvol 'DCE.nii[1]' -cost mutualinfo -report -plots -o DCE_mc.nii &> /dev/null
		if [ ! -f "DCE_mc.nii.gz" ]
			then
				echo $dir "Missing motion corrected DCE file." >> $LOG_FILE
				cd ../..
				fail=1
				continue
		else
			mkdir -p figures &> /dev/null
			max=$(python3 $SCRIPT_PATH/max_disp.py $SUBJECT_TP_PATH)
			echo -e "\e[1;33m$max\e[0m" >> $LOG_FILE
		fi
	else
		cp DCE.nii DCE_mc.nii
		gzip -f DCE_mc.nii
	fi
	fslmerge -n 1 ref_rep.nii DCE_mc.nii &> /dev/null
	gunzip -f ref_rep.nii.gz
	
	# MPRAGE -> dynamic registration
	antsRegistration --verbose 0 --dimensionality 3 --float 0 \
		--collapse-output-transforms 1 --output [ T1_dyn,T1_dynWarped.nii.gz ] \
		--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
		--transform Rigid[ 0.1 ] --metric MI[ ref_rep.nii,T1.nii,1,32,Regular,0.25 ] \
		--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox

	# VFA -> dynamic registration
	VFA_reg() {
		local VFA=$1
		antsRegistration --verbose 0 --dimensionality 3 --float 0 \
			--collapse-output-transforms 1 --output [ ${VFA}_dyn,${VFA}_dynWarped.nii.gz ] \
			--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
			--transform Rigid[ 0.1 ] --metric MI[ ref_rep.nii,${VFA}.nii,1,32,Regular,0.25 ] \
			--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
		mv ${VFA}_dynWarped.nii.gz ${VFA}_dyn.nii.gz
	}
	for VFA in "${VFA_NUMS[@]}"; do
		# VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
		VFA_reg "$VFA" &
	done
	wait
	# make array of VFA dynamic images
	VFA_DYN_LIST=($(ls -1 *_dyn.nii.gz))
	VFA_DYN_LIST=($(printf '%s\n' "${VFA_DYN_LIST[@]}" | grep -o -E '[0-9]+_dyn.nii.gz'| sort -n))

	echo -ne "T1 SEG w/ FAST [=>                                                ] $prog% ($current/$count) ~$mETA min remaining \r"
	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -g -o segmented_t1 T1_bet.nii.gz
	antsApplyTransforms -i segmented_t1_seg_2.nii.gz -r ref_rep.nii -t T1_dyn0GenericAffine.mat -o T1_wm_mask.nii.gz &> /dev/null
	ETA=$(echo "scale=0;  $mETA - ($SECONDS/60)" | bc -l)
	#ETA=$(echo "scale=0;  $mETA - $mETA * .0667" | bc -l)
	prog=$(echo "scale=2;  $prog + 6.67 / $count" | bc -l)
	

	fslmaths T1_wm_mask.nii.gz -thr 0.9 -bin T1_wm_mask.nii.gz &> /dev/null
	# copy VFA files to _masked.nii
	for VFA in "${VFA_DYN_LIST[@]}"; do
		# get VFA number
		VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
		# FAST documentation recommends brain masking first
		# fslmaths $VFA -mas T1_bet_mask.nii.gz ${VFA_NUM}_masked.nii
		cp $VFA ${VFA_NUM}_masked.nii.gz
	done
	# gzip -f *_masked.nii
	
	if [ $EN_BIAS1 -eq 1 ]
		then
			VFA_FAST () {
				local VFA=$1
				# VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o ${VFA}_masked.nii
				# ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
				# prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
				# echo -ne "BFC FAST VFA${VFA_NUM}  [=======>                                          ] $prog% ($current/$count) ~$ETA min remaining \r"
				mv ${VFA}_masked_restore* ${VFA}_bfc.nii.gz
				rm ${VFA}_masked_[mps]*

				# apply wm mask to all VFAs
				fslmaths ${VFA}_bfc.nii.gz -mas T1_wm_mask.nii.gz ${VFA}_bfc_wm.nii.gz
			}

			#echo "Bias field correction with FAST"
			# FAST every VFA
			echo -ne "BFC FAST VFAS  [=======>                                          ] $prog% ($current/$count) ~$ETA min remaining \r"
			for VFA in "${VFA_NUMS[@]}"; do
				VFA_FAST "$VFA" &
			done
			wait
			echo -ne "Z NORM VFAS    [================>                             ] $prog% ($current/$count) ~$ETA min remaining \r"
			rm -f [0-9]*_masked_[mps]*
	else
		# dumb file name management for norm only runs
		# fslmaths 2.nii -mas T1_bet_mask.nii.gz 2_bfc.nii &> /dev/null
		# fslmaths 5.nii -mas T1_bet_mask.nii.gz 5_bfc.nii &> /dev/null
		# fslmaths 10.nii -mas T1_bet_mask.nii.gz 10_bfc.nii &> /dev/null
		# fslmaths 12.nii -mas T1_bet_mask.nii.gz 12_bfc.nii &> /dev/null
		# fslmaths 15.nii -mas T1_bet_mask.nii.gz 15_bfc.nii &> /dev/null

		
		# echo "Skipping BFC... but still segmenting one VFA for matter masks"
		# fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o 15_masked.nii &> /dev/null
		# rm 15_bfc_mixeltype.nii.gz &> /dev/null
		# rm 15_bfc_pve_0.nii.gz &> /dev/null
		# rm 15_bfc_pve_1.nii.gz &> /dev/null
		# rm 15_bfc_pve_2.nii.gz &> /dev/null
		# rm 15_bfc_pveseg.nii.gz &> /dev/null
		# rm 15_bfc_seg.nii.gz &> /dev/null
		
		# threshold and binarize wm mask
		#fslmaths 15_bfc_seg.nii.gz -thr 3 -uthr 3 15_wm.nii
		
		# apply wm mask to all VFAs
		# fslmaths 2_bfc.nii -mas T1_wm_mask.nii.gz 2_bfc_wm.nii &> /dev/null
		# fslmaths 5_bfc.nii -mas T1_wm_mask.nii.gz 5_bfc_wm.nii &> /dev/null
		# fslmaths 10_bfc.nii -mas T1_wm_mask.nii.gz 10_bfc_wm.nii &> /dev/null
		# fslmaths 12_bfc.nii -mas T1_wm_mask.nii.gz 12_bfc_wm.nii &> /dev/null
		# fslmaths 15_bfc.nii -mas T1_wm_mask.nii.gz 15_bfc_wm.nii &> /dev/null
		
		# apply MP-RAGE wm mask
		for VFA in "${VFA_LIST[@]}"; do
			VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
			fslmaths ${VFA_NUM}_masked.nii.gz -mas T1_wm_mask.nii.gz ${VFA_NUM}_bfc_wm.nii.gz &> /dev/null
		done
	fi

	# Run Z-axis normalization VFA data
	# ------------------------------
	if [ $EN_Z_NORM -eq 1 ] 
		then
		#echo begin slice normalization
		python3 $SCRIPT_PATH/VFA_norm.py $SUBJECT_TP_PATH &> /dev/null
		prog=$(echo "scale=2;  $prog + .33 / $count" | bc -l)
		echo -ne "VFA MOTIONCORR [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"

		if [ ! -f "${VFA_NUMS[0]}_BFC_Z.nii" ]
			then
				echo $dir "Missing Z-normalized VFA files. Z-norm likely failed due to non-existent inputs." >> $LOG_FILE
				cd ../..
				fail=1
				continue
		fi
	else
		mkdir -p figures &> /dev/null
	fi

	if [ $EN_BIAS2 -eq 1 ]
		then
		# 2nd Bias correction VFA data
		# ------------------------------
		echo Begin second round of BFC
		# Bias field correction with FAST
		# don't forget to remove all unnecessary images
		for VFA in "${VFA_LIST[@]}"; do
			VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o ${VFA_NUM}_BFC_Z.nii ${VFA_NUM}_BFC_Z.nii &> /dev/null
			# fslmaths ${VFA_NUM}_BFC_Z.nii -div ${VFA_NUM}_BFC_Z_bias.nii.gz ${VFA_NUM}_b2corr.nii &> /dev/null
			mv ${VFA_NUM}_BFC_Z_restore* ${VFA_NUM}_b2corr.nii.gz
			rm -f ${VFA_NUM}_BFC_Z_[mps]* &> /dev/null
		done
		# concatenates all VFA images in one 4D VFA.nii.gz image

		fslmerge -t VFA.nii.gz ${VFA_NUMS[@]/%/_b2corr.nii.gz} &> /dev/null

		# remove all unnecessary images
		rm [0-9]*_BFC_Z_*
		
	elif [ $EN_Z_NORM -eq 1 ] 
		then
		#echo Concatenating Z-norm\'d images
		# concatenates VFA images in one 4D VFA.nii.gz image
		# echo ${VFA_NUMS[@]/%/_BFC_Z.nii.gz}
		fslmerge -t VFA.nii.gz ${VFA_NUMS[@]/%/_BFC_Z.nii.gz}

	elif [ $EN_BIAS1 -eq 1 ]
		then
		echo Concatenating non Z\'d images
		fslmerge -t VFA.nii ${VFA_NUMS[@]/%/_bfc.nii} &> /dev/null
	else
		echo Concatenating raw images
		fslmerge -t VFA.nii ${VFA_NUMS[@]/%/_masked.nii.gz} &> /dev/null
	fi
	
	if [ ! -f "VFA.nii.gz" ]
		then
			echo "$dir missing VFA file. Component files may have failed." >> $LOG_FILE
			cd ../..
			fail=1
			continue
	fi
	
	# motion correction of VFA
	# ------------------------------
	# if [ $EN_MOTION_CORR -eq 1 ]
	# 	then
	# 	mcflirt -in VFA.nii.gz -refvol 'VFA.nii.gz[0]' -cost mutualinfo -report -verbose -plots -o VFA_mc.nii &> /dev/null
	# else
	# 	cp VFA.nii.gz VFA_mc.nii.gz
	# fi
	prog=$(echo "scale=2;  $prog + .5 / $count" | bc -l)
	echo -ne "MAKE T1 MAPS   [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"
	gunzip -f VFA.nii.gz
	
	# if [ ! -f "VFA.nii" ]
	# 	then
	# 		echo $dir "Missing VFA file. Motion correction may have failed." >> $LOG_FILE
	# 		cd ../..
	# 		fail=1
	# 		continue
	# fi

	# T1 mapping where the input image is 'VFA.motioncorrected.nii'
	# ------------------------------
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH/parametric_scripts/custom_scripts'); addpath '$ROCKETSHIP_PATH'; \
		addpath '$ROCKETSHIP_PATH/dce'; addpath '$ROCKETSHIP_PATH/external_programs'; \
		addpath '$ROCKETSHIP_PATH/external_programs/niftitools'; addpath '$ROCKETSHIP_PATH/parametric_scripts';	\
		addpath '$GPUFIT_PATH'; addpath '$GPUFIT_M_PATH'; T1mapping_fit('$SUBJECT_TP_PATH/'); exit;" &> /dev/null
	((diff = SECONDS - diff))
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + 1.33 / $count" | bc -l)
	echo -ne "DCE MOTIONCORR [====================>                             ] $prog% ($current/$count) ~$ETA min remaining \r"
	if [ ! -f "T1_map_t1_fa_fit_VFA.nii" ]
		then
			echo $dir "Missing T1 map file. T1 mapping may have failed." >> $LOG_FILE
			cd ../..
			fail=1
			continue
	fi


	if [ $T1_ONLY -eq 1 ]
		then
		cd ../..
		continue
	fi
	
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
	echo -ne "REG T1 MAP->DCE[=======================>                          ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	# Align T1 map with Dynamic data
	# ------------------------------

	#prog=$(echo "scale=2;  $prog + .55 / $count" | bc -l)
	#echo -ne "ANTSREG T1->DCE[=======================>                          ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	prog=$(echo "scale=2;  $prog + 2.77 / $count" | bc -l)
	echo -ne "REG BET MASK   [========================>                         ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	antsApplyTransforms -i T1_bet_mask.nii.gz -r ref_rep.nii -t T1_dyn0GenericAffine.mat -o T1_bet_mask_dyn_pv.nii &> /dev/null
	fslmaths T1_bet_mask_dyn_pv.nii -thr 1 -bin T1_bet_mask_dyn.nii.gz &> /dev/null
	rm T1_bet_mask_dyn_pv.nii
	# rm T1_bet_mask_dynInverseWarped.nii.gz
	# rm T1_bet_mask_dyn0GenericAffine.mat
	prog=$(echo "scale=2;  $prog + 0.55 / $count" | bc -l)
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	echo -ne "FAST DCE REP 1 [========================>                         ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	if [ $USE_AUTO_AIF -eq 1 ]
		then
		# find AutoAIF path
		# AUTO_AIF_PATH=$(find $HOME -type d -name main_vif.py)
		AUTO_AIF_PATH=$(find $HOME -name '*main_vif.py' -printf '%h\n' -quit || find / -name '*main_vif.py' -printf '%h\n' -quit) &> /dev/null
		# run AutoAIF
		# conda activate tf
		python3 $AUTO_AIF_PATH/main_vif.py --mode inference --input_path $PWD/DCE_mc.nii.gz --save_output_path $PWD \
			--model_weight_path /media/network_mriphysics/USC-PPG/AI_training/weights/good_ones?/run2_fullMAE/model_weight.h5 \
			--save_image 1 &> /dev/null
		# conda deactivate
		# rename output
		mv *float_mask.nii aif_floats.nii
		mv DCE_mc_mask.nii aif_topvoxels.nii
		mv DCE_mc_curve.svg figures/DCE_mc_curve.svg
		mv DCE_mc_mask.svg figures/DCE_mc_mask.svg
		# fslmaths aif_floats.nii -thr 0.95 aif_mask.nii
		fslmaths T1_map_t1_fa_fit_VFA.nii -mas aif_topvoxels.nii aif.nii
		gunzip -f aif.nii.gz
	fi
	# ensure AIF is included in mask
	# fslcpgeom 2.nii T1_bet_mask_dyn.nii.gz
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
			reps=$(fslnvols DCE_mc_masked.nii)
			rep_interval=$((reps / 8))
			# round rep_interval up
			rep_interval=$(echo "scale=0; ($rep_interval + 0.5) / 1" | bc -l)

			# take 9 repetitions with rep_interval from DCE_mc_masked.nii
			fslmerge -n 0 rep_0.nii DCE_mc_masked.nii &> /dev/null
			for i in {1..8}
			do
				# name file with rep_interval*i
				fslmerge -n $((rep_interval*i-1)) rep_$((rep_interval*i-1)).nii DCE_mc_masked.nii &> /dev/null
			done

			DCE_FAST () {
				local i=$1
				local rep_interval=$2
				# if i is 0, then we're on the first repetition
				if [ ! $i -eq 0 ]
					then
					# run FAST on rep_interval*i
					fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o rep_$((rep_interval*i-1)).nii
				else
					# run FAST on first repetition
					fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o rep_0.nii
				fi
			}
			

			# BFC each repetition
			# fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o rep_0.nii &> /dev/null
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
			echo -ne "FAST DCE 8REPS [===========================>                      ] $prog% ($current/$count) ~$ETA min remaining \r"
			DCE_FAST "0" "$rep_interval" &
			for i in {1..8}
			do
				DCE_FAST "$i" "$rep_interval" &
				# echo -ne "FAST DCE REP $((rep_interval*i-1)) [====================================>             ] $prog% ($current/$count) ~$ETA min remaining \r"
			done
			wait
			ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
			prog=$(echo "scale=2;  $prog + 48 / $count" | bc -l)
			echo -ne "DCE BFC + NORM [================================================> ] $prog% ($current/$count) ~$ETA min remaining \r"
			
			# Concatenation1
			fslmerge -t dyn_bias.nii.gz rep_*_bias.nii.gz
	
			# Computing average across 8 bias field that have been sampled
			fslmaths dyn_bias.nii.gz -Tmean mean_dyn_bias_map.nii.gz
	
			# Normalizing motion corrected DCE image with mean bias field 
			fslmaths DCE_mc_masked.nii.gz -div mean_dyn_bias_map.nii.gz DCE_mc_bfc.nii
	
			# remove sampled files
			rm rep_*.nii.gz
		else
			echo Skipping DCE BFC because it already exists...
		fi
	else
		#echo Motion correcting dynamic set
		cp DCE_mc.nii.gz DCE_mc_bfc.nii.gz
		gunzip -f DCE_mc_bfc.nii.gz
	fi
	
	# align existing white matter mask to dynamic images and re-binarize
	#flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_wm_mask_dyn.nii
	# flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -2D -o T1_wm_mask_dyn.nii &> /dev/null
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_wm_mask.nii.gz T1_wm_mask_dyn.nii.gz
	#antsRegistrationSyN.sh -d 3 -t r -f ref_rep.nii -m T1_wm_mask.nii.gz -o T1_wm_mask_dyn
	# if [ $USE_FREESURFER -eq 1 ] || [ $dir == "203450/1st_timepoint/" ]
	# 	then
	# 	flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -2D -o T1_wm_mask_dyn_pv.nii &> /dev/null
	# else
	antsApplyTransforms -i T1_wm_mask.nii.gz -r ref_rep.nii -t T1_bet_dyn0GenericAffine.mat -o T1_wm_mask_dyn_pv.nii &> /dev/null
	# fi
	#mv T1_wm_mask_dynWarped.nii.gz T1_wm_mask_dyn.nii.gz
	# fslmaths T1_wm_mask_dyn_pv.nii -thr 0.9 -bin T1_wm_mask_dyn.nii.gz &> /dev/null
	
	#fslmaths T1_wm_mask_dynWarped.nii -thr 0.7 -bin T1_wm_mask_dyn.nii
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_bet_mask.nii.gz T1_bet_mask_dyn.nii.gz
	#fslmaths 15_wm_mask_dyn.nii.gz -thr 1.7 -bin 15_wm_mask_dyn.nii
	#rm T1_wm_mask_dynInverseWarped.nii.gz
	#rm T1_wm_mask_dyn0GenericAffine.mat

	# if first slice is all 0, replace it with masked second slice
	# fslroi T1_wm_mask.nii.gz first_wm_slice.nii.gz 0 -1 0 -1 0 1
	# fslroi T1_wm_mask.nii.gz last_wm_slice.nii.gz 0 -1 0 -1 -1 1

	# # get sum of first slice
	# sum=$(fslstats first_wm_slice.nii.gz -V | awk '{print $2}')
	# # convert sum to int
	# sum=${sum%.*}
	# # if sum is 0, replace first slice with second slice
	# if [ $sum -lt 1 ]
	# 	then
	# 	fslroi T1_wm_mask.nii.gz second_wm_slice.nii.gz 0 -1 0 -1 1 1
	# 	fslroi T1_wm_mask.nii.gz T1_wm_mask.nii.gz 0 -1 0 -1 1 -1
	# 	fslroi T1_wm_mask.nii.gz T1_wm_mask.nii.gz 0 -1 0 -1 0 -1
	# 	fslmerge -z T1_wm_mask.nii.gz second_wm_slice.nii.gz T1_wm_mask.nii.gz
	# 	rm first_wm_slice.nii.gz second_wm_slice.nii.gz
	# fi
	
	# apply wm mask to all DCE images
	fslmaths DCE_mc_bfc.nii -mas T1_wm_mask.nii.gz DCE_mc_bfc_wm.nii.gz &> /dev/null


	# normalize dynamic images
	# ------------------------------
	#echo Normalizing dynamic images...
	if [ $EN_Z_NORM -eq 1 ]
		then
		python3 $SCRIPT_PATH/DCE_norm.py $SUBJECT_TP_PATH
	else
		cp DCE_mc_bfc.nii DCE_mc_bfc_norm.nii
	fi

	if [ ! -f "DCE_mc_bfc_norm.nii" ]
		then
			echo $dir "Missing normalized DCE file." >> $LOG_FILE
			cd ../..
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
	echo -ne "PREP COMPLETED [==================================================] $prog% ($current/$count)"

((failures=count-successes))
echo Completed preprocessing for $count cases. >> $LOG_FILE
echo $successes subjects succeeded >> $LOG_FILE
echo $failures subjects failed >> $LOG_FILE

if [ $fail -eq 1 ]
	then
	exit 1
fi
