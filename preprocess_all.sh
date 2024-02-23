#!/bin/bash
shopt -s extglob
# FSL, Matlab, ROCKETSHIP + parametric_scripts, ANTS, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
# variables
COMPARISON_MODE=0
EN_Z_NORM=0
EN_BIAS1=0
EN_BIAS2=0
EN_MOTION_CORR=0
T1_ONLY=0
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
while getopts ":d:bBAZfhcC::mst" options; do
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
		C)
			COMPARISON_MODE=1
			OUTPUT_DIR=${OPTARG}
			;;
		c)
			clean=1
			;;
		d)
			DATA_DIR=${OPTARG}
			if [ ${DATA_DIR::-1} == "/" ]
				then
				DATA_DIR=${DATA_DIR::-1}
			fi
			DATE=$(date +%Y-%m-%d)
			# make log directory if it doesn't exist
			if [ ! -d "$DATA_DIR/logs" ]
				then
				mkdir -p "$DATA_DIR/logs"
			fi
			LOG_FILE=$DATA_DIR/logs/preprocessing_log_$DATE.txt
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, preprocessing every folder ending in '_timepoint'."
			echo "The output is the DCE input, which are the corrected dynamic images, brain mask, T1 maps."
			echo "-A: enable AutoAIF"
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-c: clean generated files prior to processing"
			echo "-C [name]: enable comparison mode, which will output all files to the specified directory within each timepoint"
			echo "-d [dir_path]: specify main data directory containing all subject folders"
			echo "-h: display this message"
			echo "-m: enable motion correction"
			echo "-s: skip preprocessing if DCE input file already exists"
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
for dir in */*_timepoint/; do
	dir=$DATA_DIR/${dir::-1}
	date >> $LOG_FILE
	echo "Preprocessing ${dir}..."
	((current++))
	cd $dir || exit 1
	gzip -f $dir/DCE.nii &> /dev/null
	if [ $COMPARISON_MODE -eq 1 ]
		then
		if [ ! -d "$OUTPUT_DIR" ]
			then
			echo "Comparison mode enabled. Creating output directory $OUTPUT_DIR..." >> $LOG_FILE
			mkdir -p "$OUTPUT_DIR"
		fi
		cd "$OUTPUT_DIR" || exit 1
		cp $dir/*.json .
	fi
	SUBJECT_TP_PATH=$(pwd)

	if [ $SKIP_IF_SUCCESS -eq 1 ]
		then
		if [ -f "DCE_mc_bfc_norm.nii.gz" ] || [ -f "case_report.html" ]
			then
			echo "Skipping ${dir} because it has already been processed." >> $LOG_FILE
			let successes++
			cd $DATA_DIR
			continue
		fi
	fi

	# get list of VFAs
	VFA_LIST=($(ls -1 $dir/*.nii | grep -v "$dir/DCE.nii.gz" | grep -v "$dir/T1.nii" | grep -v "$dir/aif.nii"))
	# sort VFAs
	VFA_LIST=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o -E '[0-9]+.nii'| sort -n))
	echo "Found ${#VFA_LIST[@]} VFAs: ${VFA_LIST[@]}"
	VFA_NUMS=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o '[0-9]*'))
	# error if no VFAs found
	if [ ${#VFA_LIST[@]} -eq 0 ]
		then
		echo "$dir No VFAs found! Skipping timepoint..." >> $LOG_FILE
		cd $DATA_DIR
		continue
	fi

	if [ ! -f "$dir/2.nii" ] || [ ! -f "$dir/5.nii" ] || [ ! -f "$dir/10.nii" ] || [ ! -f "$dir/12.nii" ] || [ ! -f "$dir/15.nii" ] || [ ! -f "$dir/DCE.nii.gz" ] || [ ! -f "$dir/T1.nii" ]
	then
		missing_files=""
		[ ! -f "$dir/2.nii" ] && missing_files+=" 2.nii"
		[ ! -f "$dir/5.nii" ] && missing_files+=" 5.nii"
		[ ! -f "$dir/10.nii" ] && missing_files+=" 10.nii"
		[ ! -f "$dir/12.nii" ] && missing_files+=" 12.nii"
		[ ! -f "$dir/15.nii" ] && missing_files+=" 15.nii"
		[ ! -f "$dir/DCE.nii.gz" ] && missing_files+=" DCE.nii.gz"
		[ ! -f "$dir/T1.nii" ] && missing_files+=" T1.nii"

		echo "$dir Base file(s) missing! Missing file(s):$missing_files. Skipping timepoint..." >> "$LOG_FILE"
		cd $DATA_DIR
		continue
	fi
	
	if [ $clean -eq 1 ]
		then
		echo Cleaning folder...
        # rm -f !(2.nii|5.nii|10.nii|12.nii|15.nii|DCE.nii|aif.nii|T1.nii|*.json)
		# remove all files except for the VFA list, DCE, AIF, T1, and json files
		rm -dfr !([0-9]*.nii|DCE.nii.gz|aif.nii|T1.nii|*.json)
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
			hd-bet -i $dir/T1.nii -o $SUBJECT_TP_PATH/T1_bet &> /dev/null
			mETA=$(echo "scale=0;  $SECONDS * 34 * ($count - $current + 1) / 60" | bc -l)
		else
			# 2-3 hours
			hd-bet -i $dir/T1.nii -o $SUBJECT_TP_PATH/T1_bet -device cpu &> /dev/null
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
		mcflirt -in $dir/DCE.nii.gz -refvol '${dir}/DCE.nii.gz[1]' -cost mutualinfo -report -plots -o DCE_mc.nii &> /dev/null
		if [ ! -f "DCE_mc.nii.gz" ]
			then
				echo $dir "Missing motion corrected DCE file." >> $LOG_FILE
				cd $DATA_DIR
				fail=1
				continue
		else
			mkdir -p figures &> /dev/null
			max=$(python3 $SCRIPT_PATH/max_disp.py $SUBJECT_TP_PATH)
			echo -e "\e[1;33m$max\e[0m" >> $LOG_FILE
		fi
	else
		cp $dir/DCE.nii.gz DCE_mc.nii.gz
	fi
	fslmerge -n 1 ref_rep.nii DCE_mc.nii &> /dev/null
	gunzip -f ref_rep.nii.gz
	
	# MPRAGE -> dynamic registration
	antsRegistration --verbose 0 --dimensionality 3 --float 0 \
		--collapse-output-transforms 1 --output [ T1_dyn,T1_dynWarped.nii.gz ] \
		--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
		--transform Rigid[ 0.1 ] --metric MI[ ref_rep.nii,${dir}/T1.nii,1,32,Regular,0.25 ] \
		--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox

	# VFA -> dynamic registration
	VFA_reg() {
		local VFA=$1
		antsRegistration --verbose 0 --dimensionality 3 --float 0 \
			--collapse-output-transforms 1 --output [ ${VFA}_dyn,${VFA}_dynWarped.nii.gz ] \
			--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
			--transform Rigid[ 0.1 ] --metric MI[ ref_rep.nii,${dir}/${VFA}.nii,1,32,Regular,0.25 ] \
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
				cd $DATA_DIR
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
			cd $DATA_DIR
			fail=1
			continue
	fi
	
	prog=$(echo "scale=2;  $prog + .5 / $count" | bc -l)
	echo -ne "MAKE T1 MAPS   [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"
	gunzip -f VFA.nii.gz
	
	# T1 mapping where the input image is 'VFA.nii'
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
			cd $DATA_DIR
			fail=1
			continue
	fi

	if [ $T1_ONLY -eq 1 ]
		then
		cd $DATA_DIR
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
	prog=$(echo "scale=2;  $prog + 0.55 / $count" | bc -l)
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	echo -ne "FAST DCE REP 1 [========================>                         ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	if [ $USE_AUTO_AIF -eq 1 ]
		then
		# find AutoAIF path
		AUTO_AIF_PATH=$(find $HOME -name '*main_vif.py' -printf '%h\n' -quit || find / -name '*main_vif.py' -printf '%h\n' -quit) &> /dev/null
		# run AutoAIF
		# conda activate tf
		python3 $AUTO_AIF_PATH/main_vif.py --mode inference --input_path $PWD/DCE_mc.nii.gz --save_output_path $PWD \
			--model_weight_path /media/network_mriphysics/USC-PPG/AI_training/weights/good_ones?/rg_10-13/model_weight.h5 \
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
				fslmerge -n $((rep_interval*i-1)) rep_$((rep_interval*i-1)).nii DCE_mc_masked.nii & &> /dev/null
			done
			wait

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
	# antsApplyTransforms -i T1_wm_mask.nii.gz -r ref_rep.nii -t T1_dyn0GenericAffine.mat -o T1_wm_mask_dyn_pv.nii &> /dev/null
	
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
	gzip -f DCE_mc_bfc_norm.nii

	if [ ! -f "DCE_mc_bfc_norm.nii.gz" ]
		then
			echo $dir "Missing normalized DCE file." >> $LOG_FILE
			cd $DATA_DIR
			fail=1
			continue
	fi

	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + .6 / $count" | bc -l)
	echo -ne "SUBJ COMPLETED [==================================================] $prog% ($current/$count) ~$ETA min remaining \r"

	cd $DATA_DIR
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
