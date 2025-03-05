#!/bin/bash
shopt -s extglob
# FSL, Matlab, ROCKETSHIP, ANTS, Python, and a BIDS compliant dataset are required
# variables
COMPARISON_MODE=0
EN_Z_NORM=0
EN_BIAS1=0
EN_BIAS2=0
EN_MOTION_CORR=0
T1_ONLY=0
USE_AUTO_AIF=0
AIF_SUFFIX="desc-AIF_mask"
AIF_TRAINING_SUFFIX="desc-trainingAIF_mask"
SKIP_IF_SUCCESS=0
SCRIPT_LOOP_DIRS=sub-*/ses-*
AUTOAIF_WEIGHT_PATH="/media/network_mriphysics/USC-PPG/AI_training/weights/huber_real/model_weight_huber1.h5"
AUTOAIF_MODEL="best"

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
while getopts ":d:bBa:A:ZfhcC:mMstl:T:w:" options; do
	case "${options}" in
		a)
			AIF_SUFFIX=${OPTARG}
			;;
		A)
			AUTO_AIF_PATH=$(find $HOME -wholename '*main_vif.py' -printf '%h\n' -quit || find / -name '*main_vif.py' -printf '%h\n' -quit) &> /dev/null
			case "${OPTARG}" in
				M)
					USE_AUTO_AIF=0
					;;
				A)
					USE_AUTO_AIF=1
					;;
				T)
					USE_AUTO_AIF=2
					;;
				*)
					echo "Invalid argument for -A. Use A, M, or T."
					exit 1
					;;
			esac
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
			# derivatives dir is up 1 level from data dir
			DERIV_DIR=$(dirname $DATA_DIR)/derivatives
			if [ ! -d "$DERIV_DIR" ]
				then
				mkdir -p "$DERIV_DIR"
			fi
			# make log directory if it doesn't exist
			if [ ! -d "$DERIV_DIR/logs" ]
				then
				mkdir -p "$DERIV_DIR/logs"
			fi
			LOG_FILE=$DERIV_DIR/logs/preprocessing_log_$DATE.txt
			# write command to log file
			echo "Command: $0 $@" > $LOG_FILE
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, preprocessing every folder ending in '_timepoint'."
			echo "The output is the DCE input, which are the corrected dynamic images, brain mask, T1 maps."
			echo "-a: specify AIF suffix (default is 'desc-AIF_mask'). .nii.gz will be appended to the suffix."
			echo "-A: enable AutoAIF with argument A (All automatic), M (Manual if available), or T (Manual + Training if available)"
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-c: clean case's derivative folder prior to processing, ensures \"fresh\" runs but cannot use skips"
			echo "-C [name]: enable comparison mode, which will output all files to the specified directory within each timepoint"
			echo "-d [dir_path]: specify BIDS compliant data directory containing all subject folders (sub-*/ses-*/anat|dce/*.nii|*.json)"
			echo "-h: display this message"
			echo "-m: enable motion correction"
			echo "-s: skip preprocessing if DCE input file already exists"
			echo "-T [dir_path]: target the subject(s)/session(s) to run (default is 'sub-*/ses-*/')"
			echo "-t: only run up to T1 mapping"
			echo "-w [path]: specify the path to the AutoAIF weights file"
			echo "-Z: enable Z-slice normalization"
			exit 0
			;;
		l)
			INPUT_LIST=$DATA_DIR/../code/${OPTARG}
			;;
		m)
			EN_MOTION_CORR=1
			;;
		M)
			AUTOAIF_MODEL=${OPTARG}
			;;
		s)
			SKIP_IF_SUCCESS=1
			;;
		S)
			SCRIPT_LOOP_DIRS=${OPTARG}
			;;
		t)
			T1_ONLY=1
			;;
		w)
			AUTOAIF_WEIGHT_PATH=${OPTARG}
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
		echo "ERROR: Please use '-d [dir_path]' to pass the path to your BIDS compliant data directory to this script."
		exit 1
fi

if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(find $HOME -name '*run_dce_cli.m' -printf '%h\n' -quit || find / -name '*run_dce_cli.m' -printf '%h\n' -quit) &> /dev/null
	SCRIPT_PATH=$(dirname "$(realpath $0)")
	GPUFIT_PATH=$(find $HOME -name 'GpufitCudaAvailableMex.mexa64' -printf '%h\n' -quit || find / -name 'GpufitCudaAvailableMex.mexa64' -printf '%h\n' -quit) &> /dev/null
	GPUFIT_M_PATH=$(find $HOME -name 'ModelID.m' -printf '%h\n' -quit || find / -name 'ModelID.m' -printf '%h\n' -quit)
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
	GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
fi
cd $DATA_DIR || exit 1

# count timepoints
for source_dir in $DATA_DIR/$SCRIPT_LOOP_DIRS; do
	((count++))
done
# Function to calculate and display progress and estimated remaining time
function show_progress {
    local current_iteration=$1
    local start_time=$2
    local total_iterations=$3
	local runtime=$4

    # Calculate elapsed time
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))

    # Calculate estimated total time
    estimated_total_time=$((runtime * total_iterations))

    # Calculate remaining time
    remaining_time=$((estimated_total_time - elapsed_time))

    # Display progress and estimated remaining time
    echo -ne "Progress: $((elapsed_time * 100 / estimated_total_time))% - "
    echo -ne "Elapsed time: $(($elapsed_time / 60))m $(($elapsed_time % 60))s - "
	if [ $remaining_time -lt 0 ]
		then
		echo -ne "Estimated remaining time: calculating...\r"
	else
		echo -ne "Estimated remaining time: $(($remaining_time / 60))m $(($remaining_time % 60))s\r"
	fi
}
# Run bias correction on VFA data
# ------------------------------
for source_dir in $DATA_DIR/$SCRIPT_LOOP_DIRS; do
	start_time=$(date +%s)
	if [ ${source_dir::-1} == "/" ]; then
		source_dir=$DATA_DIR/${source_dir::-1}
	fi
	date >> $LOG_FILE
	echo "Preprocessing ${source_dir}..."
	((current++))

	# get subject ID and session
	SUBJECT=$(echo $source_dir | grep -o 'sub-[^/]*')
	SESSION=$(echo $source_dir | grep -o 'ses-[0-9]*')
	PREFIX=${SUBJECT}_${SESSION}

	if [ $COMPARISON_MODE -eq 1 ]
		then
		if [ ! -d "$DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION" ]
			then
			echo "Comparison mode enabled. Creating output directory $OUTPUT_DIR..." >> $LOG_FILE
			mkdir -p $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce
		fi
		if [ ! $USE_AUTO_AIF -eq 1 ]
			then
			mask_copied=0
			cp $DERIV_DIR/dceprep-manualAIF_refresh/$SUBJECT/$SESSION/dce/*$AIF_SUFFIX* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/ && mask_copied=1
			# cp $DERIV_DIR/dceprep/$SUBJECT/$SESSION/dce/*$AIF_TRAINING_SUFFIX* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/ && mask_copied=1
			# Extract the session number from the session string
			session_num=$(echo $SESSION | grep -o '[0-9]\+')
			# turn sub-* into *
			pat=${SUBJECT#sub-}
			# Map the session number to the corresponding session string
			case $session_num in
				01) session_str="1st" ;;
				02) session_str="2nd" ;;
				03) session_str="3rd" ;;
				*) session_str="" ;;
			esac
			# If the session string is not empty, copy the masks
			if [ $mask_copied -eq 0 ] && [[ -n $session_str ]]; then
				echo "Copying masks for $SUBJECT $SESSION..." >> $LOG_FILE
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/test/masks/sub-${pat}_ses-${session_num}_desc-AIF_mask.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/test/masks/${pat}_${session_str}_timepoint.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/train/masks/sub-${pat}_ses-${session_num}_desc-AIF_mask.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/train/masks/${pat}_${session_str}_timepoint.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/val/masks/sub-${pat}_ses-${session_num}_desc-AIF_mask.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/val/masks/${pat}_${session_str}_timepoint.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
			fi
			if [ $mask_copied -eq 0 ] && [ ! -f $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${PREFIX}_${AIF_SUFFIX}.nii.gz ] && [ ! -f $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz ] && [ $USE_AUTO_AIF -eq 2 ]
				then
				echo "No AIF file found for $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/. Skipping timepoint..." >> $LOG_FILE
				rm -rf $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION
				if [ -z "$(ls -A $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT)" ]
					then
					rm -rf $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT
				fi
				cd $DATA_DIR
				continue
			fi
		fi
		cd $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION || exit 1
	else
		mkdir -p $DERIV_DIR/dceprep/$SUBJECT/$SESSION
		cd $DERIV_DIR/dceprep/$SUBJECT/$SESSION || exit 1
	fi
	SUBJECT_TP_PATH=$(pwd)

	if [ ! -f $DERIV_DIR/dceprep/$SUBJECT/$SESSION/dce/${PREFIX}_${AIF_SUFFIX}.nii.gz ] && [ ! -f $DERIV_DIR/dceprep-manualAIF/$SUBJECT/$SESSION/dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz ] && [ $USE_AUTO_AIF -eq 2 ]
		then
		echo "No ${PREFIX}_$AIF_SUFFIX file found for $DERIV_DIR/dceprep/$SUBJECT/$SESSION/. Skipping timepoint..." >> $LOG_FILE
		cd $DATA_DIR
		continue
	fi

	if [ $SKIP_IF_SUCCESS -eq 1 ]
		then
		if [ -f "dce/${PREFIX}_desc-bfcz_DCE.nii.gz" ] && [ -f "anat/${PREFIX}_space-DCEref_desc-brain_mask.nii.gz" ] && \
			[ -f "dce/${PREFIX}_desc-AIF_T1map.nii.gz" ] && [ -f "anat/${PREFIX}_space-DCEref_T1map.nii" ] #&& [ -f "reports/${PREFIX}_desc-casereport.html" ]
			then
			echo "Skipping ${source_dir} because it has already been processed." >> $LOG_FILE
			let successes++
			cd $DATA_DIR
			continue
		fi
	fi

	# get list of VFAs and sort them
	VFA_LIST=($(ls $source_dir/anat/*.nii* | grep -v "$source_dir/anat/*T1w.nii*" | grep -v "$source_dir/dce/*aif.nii*"))
	VFA_LIST=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o -E 'flip-[0-9]+' | sort -n))
	echo "Found ${#VFA_LIST[@]} VFAs: ${VFA_LIST[@]}"
	VFA_NUMS=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o -E 'flip-[0-9]+' | grep -o -E '[0-9]+'))

	if [ ${#VFA_LIST[@]} -eq 0 ]
		then
		echo "$source_dir No VFAs found! Skipping timepoint..." >> $LOG_FILE
		cd $DATA_DIR
		continue
	fi

	if [ ! -f "$source_dir/dce/${PREFIX}_DCE.nii.gz" ] || [ ! -f "$source_dir/anat/${PREFIX}_T1w.nii.gz" ]
	then
		missing_files=""
		[ ! -f "$source_dir/dce/${PREFIX}_DCE.nii.gz" ] && missing_files+=" $source_dir/dce/${PREFIX}_DCE.nii.gz"
		[ ! -f "$source_dir/anat/${PREFIX}_T1w.nii.gz" ] && missing_files+=" $source_dir/anat/${PREFIX}_T1w.nii.gz"

		echo "$source_dir Base file(s) missing! Missing file(s):$missing_files. Skipping timepoint..." >> "$LOG_FILE"
		cd $DATA_DIR
		continue
	fi

	mkdir dce &> /dev/null
	if [ $clean -eq 1 ]
		then
		echo Cleaning folder... $PWD
		# remove all files except for the AIF
		rm -rf anat figures reports
		cd dce
		rm -f !(${PREFIX}_${AIF_SUFFIX}.nii.gz|${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz)
		cd $SUBJECT_TP_PATH
    fi
	mkdir anat &> /dev/null

	# HD-BET brain extraction & segmentations from MP-RAGE
	SECONDS=0
	echo -ne "HD-BET MP-RAGE [                                                  ] $prog% ($current/$count) Calculating runtime...   \r"

	if [ ! -f "anat/${PREFIX}_desc-brain_mask.nii.gz" ] && [ -f "$source_dir/anat/${PREFIX}_T1w.nii.gz" ]
		then
		if [ nvidia-smi ]
			then
			hd-bet -i $source_dir/anat/${PREFIX}_T1w.nii.gz -o anat/${PREFIX}_desc-brain &> /dev/null
			mETA=$(echo "scale=0;  $SECONDS * 34 * ($count - $current + 1) / 60" | bc -l)
		else
			hd-bet -i $source_dir/anat/${PREFIX}_T1w.nii.gz -o anat/${PREFIX}_desc-brain -device cpu &> /dev/null
			mETA=$(echo "scale=0;  $SECONDS * 2 * ($count - $current + 1) / 60" | bc -l)
		fi
		mv anat/${PREFIX}_desc-brain.nii.gz anat/${PREFIX}_desc-brain_T1w.nii.gz
	elif [ -f "$source_dir/anat/${PREFIX}_T2w.nii.gz" ]
		then
		# assume mouse
		# we gotta do some orientation shenanigans
		echo
	fi
	prog=$(echo "scale=2;  $prog + 3.33 / $count" | bc -l)

	# Motion correction of dynamic images to 2nd rep using FSL
	# ------------------------------
	if [ $EN_MOTION_CORR -eq 1 ]
		then
		if [ ! -f "dce/${PREFIX}_desc-hmc_DCE.nii.gz" ]
			then
			mcflirt -in $source_dir/dce/${PREFIX}_DCE.nii.gz -refvol '${source_dir}/dce/${PREFIX}_DCE.nii.gz[1]' -cost mutualinfo -report -plots -o dce/${PREFIX}_desc-hmc_DCE.nii &> /dev/null
			if [ ! -f "dce/${PREFIX}_desc-hmc_DCE.nii.gz" ]
				then
				echo $SUBJECT_TP_PATH/dce "Missing motion corrected DCE file." >> $LOG_FILE
				cd $DATA_DIR
				fail=1
				continue
			fi
		fi
		# mkdir -p $source_dir/figures &> /dev/null
		mkdir -p figures &> /dev/null
		max=$(python3 $SCRIPT_PATH/max_disp.py $SUBJECT_TP_PATH/dce ${PREFIX})
		echo -e "$max" > dce/${PREFIX}_desc-hmc_maxdisp.txt
		fslmerge -n 1 dce/${PREFIX}_desc-hmc_DCEref.nii dce/${PREFIX}_desc-hmc_DCE.nii.gz &> /dev/null
		DCE_REF_VOL=dce/${PREFIX}_desc-hmc_DCEref.nii.gz
	else
		# cp $source_dir/DCE.nii.gz DCE_mc.nii.gz
		fslmerge -n 1 dce/${PREFIX}_DCEref.nii $source_dir/dce/${PREFIX}_DCE.nii &> /dev/null
		DCE_REF_VOL=dce/${PREFIX}_DCEref.nii.gz
		# gunzip -f $source_dir/ref_rep_noMC.nii.gz
	fi

	REF_SPACE=space-DCEref
	if [ ! -f anat/${PREFIX}_from-T1w_to-DCEref.mat ] && [ $EN_MOTION_CORR -eq 1 ]
		then
		# MPRAGE -> dynamic registration
		antsRegistration --verbose 0 --dimensionality 3 --float 0 \
			--collapse-output-transforms 1 --output [ anat/${PREFIX}_${REF_SPACE}_T1w,anat/${PREFIX}_${REF_SPACE}_T1w.nii.gz ] \
			--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
			--transform Rigid[ 0.1 ] --metric MI[ $DCE_REF_VOL,${source_dir}/anat/${PREFIX}_T1w.nii.gz,1,32,Regular,0.25 ] \
			--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
		mv anat/${PREFIX}_${REF_SPACE}_T1w0GenericAffine.mat anat/${PREFIX}_from-T1w_to-DCEref.mat
	elif [ $EN_MOTION_CORR -eq 0 ]
		then
		antsRegistration --verbose 0 --dimensionality 3 --float 0 \
			--collapse-output-transforms 1 --output [ anat/${PREFIX}_${REF_SPACE}_T1w,anat/${PREFIX}_${REF_SPACE}_T1w.nii.gz ] \
			--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
			--transform Rigid[ 0.1 ] --metric MI[ $DCE_REF_VOL,${source_dir}/anat/${PREFIX}_T1w.nii.gz,1,32,Regular,0.25 ] \
			--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
		mv anat/${PREFIX}_${REF_SPACE}_T1w0GenericAffine.mat anat/${PREFIX}_from-T1w_to-DCEref.mat
	fi
	T1w_to_DCEref=anat/${PREFIX}_from-T1w_to-DCEref.mat
	# VFA -> dynamic registration
	VFA_reg() {
		local VFA=$1
		antsRegistration --verbose 0 --dimensionality 3 --float 0 \
			--collapse-output-transforms 1 --output [ anat/${PREFIX}_flip-${VFA}_${REF_SPACE},anat/${PREFIX}_flip-${VFA}_${REF_SPACE}_VFA.nii.gz ] \
			--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
			--transform Rigid[ 0.1 ] --metric MI[ $DCE_REF_VOL,$source_dir/anat/${PREFIX}_flip-${VFA}_VFA.nii.gz,1,32,Regular,0.25 ] \
			--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
		# mv anat/${VFA}_dynWarped.nii.gz anat/${VFA}_dyn.nii.gz
		# TODO: re-register with fewer iterations if any slice is empty or bad
		mv anat/${PREFIX}_flip-${VFA}_${REF_SPACE}0GenericAffine.mat anat/${PREFIX}_from-VFA${VFA}_to-DCEref.mat
	}

	for VFA in "${VFA_NUMS[@]}"; do
		if [ ! -f "anat/${PREFIX}_flip-${VFA}_VFA.nii.gz" ]
			then
			VFA_reg "$VFA" &
		fi
	done
	wait
	# make array of VFA dynamic images
	VFA_DYN_LIST=($(ls -1 anat/${PREFIX}_flip-*.nii*))
	VFA_DYN_LIST=($(printf '%s\n' "${VFA_DYN_LIST[@]}" | grep -o -E 'flip-[0-9]+*'| sort -n | uniq))

	# logic for dealing with empty slices due to registration
	# check slices of each VFA, discard empty slices from ALL images
	for VFA in "${VFA_DYN_LIST[@]}"; do
		fslslice anat/${PREFIX}_${VFA}_${REF_SPACE}_VFA.nii.gz anat/${PREFIX}_${VFA}_${REF_SPACE}_VFA
	done

	# check if any slices are empty
	EMPTY_SLICES=0
	problem_slice=0
	for slice in $(ls -1 anat/${PREFIX}_${VFA}_${REF_SPACE}_VFA*.nii*); do
		if [ $(fslstats $slice -V | awk '{print $1}') -lt 100 ]
			then
			rm $slice
			# remove corresponding slice from all VFAs
			slice=$(echo $slice | grep -o -E '_[0-9]+.nii' | grep -o -E '[0-9]+')
			rm anat/${PREFIX}_flip-*_${REF_SPACE}_VFA_slice_$slice.nii*
			problem_slice=$slice
			EMPTY_SLICES=1
			echo "Removing empty slice $slice from all images" >> $LOG_FILE
		fi
	done

	if [ $EMPTY_SLICES -eq 1 ]
		then
		anat_files=$(ls anat/*${REF_SPACE}*.nii* | grep -v "slice")
		echo $anat_files
		for registered_img in $anat_files; do
			echo "Re-merging $registered_img"
			reg_img_no_ext=${registered_img%.nii*}
			reg_img_no_ext=${reg_img_no_ext%_slice_*}
			fslslice $registered_img $reg_img_no_ext
			rm ${reg_img_no_ext}_slice_$problem_slice.nii*
			fslmerge -z $registered_img ${reg_img_no_ext}_slice_*.nii* &> /dev/null
		done
		dce_files=$(ls dce/*.nii* | grep -v "slice" | grep -v ".par")
		for img in $dce_files; do
			img_no_ext=${img%.nii*}
			img_no_ext=${img_no_ext%_slice_*}
			fslslice $img $img_no_ext
			rm ${img_no_ext}_slice_$problem_slice.nii*
			fslmerge -z $img ${img_no_ext}_slice_*.nii* &> /dev/null
		done
		# re-merge VFAs
		for VFA in "${VFA_DYN_LIST[@]}"; do
			fslmerge -z anat/${PREFIX}_${VFA}_${REF_SPACE}_VFA.nii.gz anat/${PREFIX}_${VFA}_${REF_SPACE}_VFA_slice_*.nii* &> /dev/null
		done
		rm anat/*slice_*.nii* dce/*slice_*.nii*
	else
		rm anat/*slice_*.nii*
	fi

	if [ ! -f anat/${PREFIX}_label-WM_mask.nii.gz ]
		then
		echo -ne "T1 SEG w/ FAST [=>                                                ] $prog% ($current/$count) ~$mETA min remaining \r"
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -g -o anat/${PREFIX}_label- anat/${PREFIX}_desc-brain_T1w.nii.gz
		# rename segmented files
		mv anat/${PREFIX}_label-_bias.nii.gz anat/${PREFIX}_desc-bias_T1w.nii.gz
		mv anat/${PREFIX}_label-_seg_0.nii.gz anat/${PREFIX}_label-CSF_mask.nii.gz
		mv anat/${PREFIX}_label-_seg_1.nii.gz anat/${PREFIX}_label-GM_mask.nii.gz
		mv anat/${PREFIX}_label-_seg_2.nii.gz anat/${PREFIX}_label-WM_mask.nii.gz
		rm anat/${PREFIX}_label-_seg.nii.gz
		antsApplyTransforms -i anat/${PREFIX}_label-WM_mask.nii.gz -r $DCE_REF_VOL -t $T1w_to_DCEref -o anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz &> /dev/null
		ETA=$(echo "scale=0;  $mETA - ($SECONDS/60)" | bc -l)
		#ETA=$(echo "scale=0;  $mETA - $mETA * .0667" | bc -l)
		prog=$(echo "scale=2;  $prog + 6.67 / $count" | bc -l)
	fi

	fslmaths anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz -thr 0.9 -bin anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz &> /dev/null
	# copy VFA files to _masked.nii
	for VFA in "${VFA_DYN_LIST[@]}"; do
		# get VFA number
		# VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
		# FAST documentation recommends brain masking first
		# fslmaths $VFA -mas T1_bet_mask.nii.gz ${VFA_NUM}_masked.nii
		cp anat/${PREFIX}_${VFA}_${REF_SPACE}_VFA.nii.gz anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-brain_VFA.nii.gz
	done
	# gzip -f *_masked.nii

	if [ $EN_BIAS1 -eq 1 ] && [ ! -f "anat/${PREFIX}_${VFA_LIST[0]}_${REF_SPACE}_desc-bfc_VFA.nii.gz" ]
		then
			VFA_FAST () {
				local VFA=$1
				# VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
				fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-brain_VFA.nii.gz
				# ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
				# prog=$(echo "scale=2;  $prog + 6 / $count" | bc -l)
				# echo -ne "BFC FAST VFA${VFA_NUM}  [=======>                                          ] $prog% ($current/$count) ~$ETA min remaining \r"
				mv anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-brain_VFA_restore* anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-bfc_VFA.nii.gz
				# rm ${VFA}_masked_[mps]*

				# apply wm mask to all VFAs
				fslmaths anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-bfc_VFA.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz anat/${PREFIX}_${VFA}_${REF_SPACE}_seg-WM_VFA.nii.gz
			}

			#echo "Bias field correction with FAST"
			# FAST every VFA
			echo -ne "BFC FAST VFAS  [=======>                                          ] $prog% ($current/$count) ~$ETA min remaining \r"
			for VFA in "${VFA_DYN_LIST[@]}"; do
			echo "BFC FAST $VFA"
				VFA_FAST "$VFA" &
			done
			wait
			echo -ne "Z NORM VFAS    [================>                             ] $prog% ($current/$count) ~$ETA min remaining \r"
			rm -f $source_dir/[0-9]*_masked_[mps]*
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
			# VFA_NUM=$(echo $VFA | grep -o '[0-9]*')
			fslmaths anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-brain_VFA.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz anat/${PREFIX}_${VFA}_${REF_SPACE}_seg-WM_VFA.nii.gz &> /dev/null
		done
	fi

	# Run Z-axis normalization VFA data
	# ------------------------------
	if [ $EN_Z_NORM -eq 1 ]
		then
		if [ ! -f "anat/${PREFIX}_${VFA_LIST[0]}_${REF_SPACE}_desc-bfcz_VFA.nii.gz" ]
			then
			#echo begin slice normalization
			python3 $SCRIPT_PATH/VFA_norm.py $SUBJECT_TP_PATH/anat $PREFIX $EN_BIAS1 &> /dev/null
			prog=$(echo "scale=2;  $prog + .33 / $count" | bc -l)
			echo -ne "VFA MOTIONCORR [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"
		fi
		if [ ! -f "anat/${PREFIX}_${VFA_LIST[0]}_${REF_SPACE}_desc-bfcz_VFA.nii.gz" ]
			then
				echo $source_dir "Missing Z-normalized VFA files. Z-norm likely failed due to non-existent inputs." >> $LOG_FILE
				cd $DATA_DIR
				fail=1
				continue
		fi
	else
		mkdir -p figures &> /dev/null
	fi
	
	VFA_INPUT=""
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
			mv ${VFA_NUM}_BFC_Z_restore* ${VFA_NUM}_bfc2.nii.gz
			rm -f ${VFA_NUM}_BFC_Z_[mps]* &> /dev/null
		done
		# concatenates all VFA images in one 4D VFA.nii.gz image
		fslmerge -t VFA.nii.gz ${VFA_NUMS[@]/%/_bfc2.nii.gz} &> /dev/null

		# remove all unnecessary images
		rm [0-9]*_BFC_Z_*
		
	elif [ $EN_Z_NORM -eq 1 ] 
		then
		#echo Concatenating Z-norm\'d images
		# concatenates VFA images in one 4D VFA.nii.gz image
		# fslmerge -t $source_dir/VFA_BFC_Z.nii.gz "${VFA_NUMS[@]/#/\/$source_dir\/}"_BFC_Z.nii.gz
		for VFA in "${VFA_DYN_LIST[@]}"; do
			VFA_INPUT+="anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-bfcz_VFA.nii.gz "
		done
		fslmerge -t anat/${PREFIX}_${REF_SPACE}_desc-bfczunified_VFA.nii.gz $VFA_INPUT
		VFA_INPUT="desc-bfczunified_VFA"
	elif [ $EN_BIAS1 -eq 1 ]
		then
		# echo Concatenating non Z\'d images
		for VFA in "${VFA_DYN_LIST[@]}"; do
			VFA_INPUT+="anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-bfc_VFA.nii.gz "
		done
		fslmerge -t anat/${PREFIX}_${REF_SPACE}_desc-bfcunified_VFA.nii.gz $VFA_INPUT &> /dev/null
		VFA_INPUT="desc-bfcunified_VFA"
	else
		echo Concatenating raw images
		for VFA in "${VFA_DYN_LIST[@]}"; do
			VFA_INPUT+="anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-brain_VFA.nii.gz "
		done
		fslmerge -t anat/${PREFIX}_${REF_SPACE}_desc-unified_VFA.nii.gz $VFA_INPUT
		VFA_INPUT="desc-unified_VFA"
	fi
	gunzip -f "anat/${PREFIX}_${REF_SPACE}_$VFA_INPUT.nii.gz"
	
	if [ ! -f "anat/${PREFIX}_${REF_SPACE}_$VFA_INPUT.nii" ]
		then
			echo "$source_dir missing VFA file. Component files may have failed." >> $LOG_FILE
			cd $DATA_DIR
			fail=1
			continue
	fi
	
	prog=$(echo "scale=2;  $prog + .5 / $count" | bc -l)
	echo -ne "MAKE T1 MAPS   [===================>                              ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	# T1 mapping where the input image is 'VFA.nii'
	# ------------------------------
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH/parametric_scripts/custom_scripts'); addpath '$ROCKETSHIP_PATH'; \
		addpath '$ROCKETSHIP_PATH/dce'; addpath '$ROCKETSHIP_PATH/external_programs'; \
		addpath '$ROCKETSHIP_PATH/external_programs/niftitools'; addpath '$ROCKETSHIP_PATH/parametric_scripts';	\
		addpath '$GPUFIT_PATH'; addpath '$GPUFIT_M_PATH'; T1mapping_fit('$source_dir/anat', '$SUBJECT_TP_PATH/anat', '${PREFIX}_${REF_SPACE}_$VFA_INPUT.nii'); exit;" &> /dev/null
	mv anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_T1map.nii
	mv anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.mat anat/${PREFIX}_${REF_SPACE}_T1map.mat
	mv anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.txt anat/${PREFIX}_${REF_SPACE}_T1map.txt
	mv anat/Rsquared_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_desc-rsquared_T1map.nii
	mv anat/CI_low_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_desc-CIlow_T1map.nii
	mv anat/CI_high_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_desc-CIhigh_T1map.nii
	((diff = SECONDS - diff))
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + 1.33 / $count" | bc -l)
	echo -ne "DCE MOTIONCORR [====================>                             ] $prog% ($current/$count) ~$ETA min remaining \r"
	if [ ! -f anat/${PREFIX}_${REF_SPACE}_T1map.nii ]
		then
			echo $source_dir "Missing T1 map file. T1 mapping may have failed." >> $LOG_FILE
			cd $DATA_DIR
			fail=1
			continue
	fi

	if [ $T1_ONLY -eq 1 ]
		then
		cd $DATA_DIR
		continue
	fi
	
	# Align T1 map with Dynamic data
	# -----------------------------	
	prog=$(echo "scale=2;  $prog + 2.77 / $count" | bc -l)
	echo -ne "REG BET MASK   [========================>                         ] $prog% ($current/$count) ~$ETA min remaining \r"
	antsApplyTransforms -i anat/${PREFIX}_desc-brain_mask.nii.gz -r $DCE_REF_VOL -t $T1w_to_DCEref -o anat/${PREFIX}_${REF_SPACE}_desc-brain_mask_pv.nii.gz &> /dev/null
	fslmaths anat/${PREFIX}_${REF_SPACE}_desc-brain_mask_pv.nii.gz -thr 1 -bin anat/${PREFIX}_${REF_SPACE}_desc-brain_mask.nii.gz &> /dev/null
	rm anat/${PREFIX}_${REF_SPACE}_desc-brain_mask_pv.nii.gz
	prog=$(echo "scale=2;  $prog + 0.55 / $count" | bc -l)
	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	echo -ne "FAST DCE REP 1 [========================>                         ] $prog% ($current/$count) ~$ETA min remaining \r"
	
	mkdir -p figures &> /dev/null
	if [ $USE_AUTO_AIF -eq 1 ] || [ ! -f "dce/${PREFIX}_${AIF_SUFFIX}.nii.gz" ] && [ ! -f "dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz" ]
		then
		# run AutoAIF
		if [ $EN_MOTION_CORR -eq 1 ]
			then
			python3 $AUTO_AIF_PATH/main_vif.py --mode inference --input_path dce/${PREFIX}_desc-hmc_DCE.nii.gz --save_output_path $PWD/dce \
				--model_weight_path $AUTOAIF_WEIGHT_PATH \
				--model_name $AUTOAIF_MODEL \
				--save_image 1 &> /dev/null
			# rename output
			mv dce/${PREFIX}_desc-hmc_DCE_float_mask.nii dce/${PREFIX}_desc-AIFfloat_mask.nii
			mv dce/${PREFIX}_desc-hmc_DCE_mask.nii dce/${PREFIX}_desc-AIFtopvoxels_mask.nii
			mv dce/${PREFIX}_desc-hmc_DCE_curve.svg figures/${PREFIX}_desc-AIF_resampledcurve.svg
			mv dce/${PREFIX}_desc-hmc_DCE_mask.svg figures/${PREFIX}_desc-AIF_mask.svg
			# fslmaths aif_floats.nii -thr 0.95 aif_mask.nii
			fslmaths anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz -mas dce/${PREFIX}_desc-AIFtopvoxels_mask.nii dce/${PREFIX}_desc-AIF_T1map.nii
		else
			python3 $AUTO_AIF_PATH/main_vif.py --mode inference --input_path $source_dir/dce/${PREFIX}_DCE.nii.gz --save_output_path $PWD/dce \
				--model_weight_path $AUTOAIF_WEIGHT_PATH \
				--model_name $AUTOAIF_MODEL \
				--save_image 1 &> /dev/null
			mv dce/${PREFIX}_DCE_float_mask.nii dce/${PREFIX}_AIFfloat_mask.nii
			mv dce/${PREFIX}_DCE_mask.nii dce/${PREFIX}_AIFtopvoxels_mask.nii
			mv dce/${PREFIX}_DCE_curve.svg figures/${PREFIX}_AIF_resampledcurve.svg
			mv dce/${PREFIX}_DCE_mask.svg figures/${PREFIX}_AIF_mask.svg
			fslmaths anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz -mas dce/${PREFIX}_AIFtopvoxels_mask.nii dce/${PREFIX}_desc-AIF_T1map.nii
		fi
	elif [ $USE_AUTO_AIF -eq 2 ]
		then
		# use all available manual AIFs, including those reserved for training
		if [ -f "dce/${PREFIX}_${AIF_SUFFIX}.nii.gz" ]
			then
			# use manual AIF
			fslmaths anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz -mas dce/${PREFIX}_${AIF_SUFFIX}.nii.gz dce/${PREFIX}_desc-AIF_T1map.nii.gz
		elif [ -f "dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz" ]
			then
			# use training manual AIF
			fslmaths anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz -mas dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz dce/${PREFIX}_desc-AIF_T1map.nii.gz
		fi
	else
		# use manual AIF
		fslmaths anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz -mas dce/${PREFIX}_${AIF_SUFFIX}.nii.gz dce/${PREFIX}_desc-AIF_T1map.nii.gz
	fi
	# ensure AIF is included in mask
	# fslcpgeom 2.nii T1_bet_mask_dyn.nii.gz
	cp dce/${PREFIX}_desc-AIF_T1map.nii.gz dce/${PREFIX}_desc-AIFaligned_T1map.nii.gz
	fslcpgeom anat/${PREFIX}_${REF_SPACE}_desc-brain_mask.nii.gz dce/${PREFIX}_desc-AIFaligned_T1map.nii
	fslmaths dce/${PREFIX}_desc-AIFaligned_T1map.nii.gz -thr 0 dce/${PREFIX}_desc-AIFpos_T1map.nii &> /dev/null
	rm dce/${PREFIX}_desc-AIFaligned_T1map.nii.gz
	fslmaths anat/${PREFIX}_${REF_SPACE}_desc-brain_mask.nii.gz -add dce/${PREFIX}_desc-AIFpos_T1map.nii -thr 1 -bin anat/${PREFIX}_${REF_SPACE}_desc-brainAIF_mask.nii.gz &> /dev/null
	# apply AIF mask to all DCE images
	if [ $EN_MOTION_CORR -eq 1 ]
		then
		fslmaths dce/${PREFIX}_desc-hmc_DCE.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_desc-brainAIF_mask.nii.gz dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
	elif [ $EN_MOTION_CORR -eq 0 ] && [ $EN_BIAS1 -eq 1 ]
		then
		fslmaths dce/${PREFIX}_desc-bfc_DCE.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_desc-brainAIF_mask.nii.gz dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
	else
		fslmaths $source_dir/dce/${PREFIX}_DCE.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_desc-brainAIF_mask.nii.gz dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
	fi
		
	if [ $EN_BIAS1 -eq 1 ]
		then
		if [ ! -f "dce/${PREFIX}_desc-bfc_DCE.nii.gz" ]
			then
			# Applying bias field correction on dynamic images
			# ------------------------------
			#echo Applying BFC to dynamic images...
			reps=$(fslnvols dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz)
			rep_interval=$((reps / 8))
			# round rep_interval up
			rep_interval=$(echo "scale=0; ($rep_interval + 0.5) / 1" | bc -l)

			# take 9 repetitions with rep_interval from DCE_mc_masked.nii
			fslmerge -n 0 rep_0.nii dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
			for i in {1..8}
			do
				# name file with rep_interval*i
				fslmerge -n $((rep_interval*i-1)) rep_$((rep_interval*i-1)).nii dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz & &> /dev/null
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
			fslmerge -t dce/dyn_bias.nii.gz rep_*_bias.nii.gz
	
			# Computing average across 8 bias field that have been sampled
			fslmaths dce/dyn_bias.nii.gz -Tmean dce/mean_dyn_bias_map.nii.gz
	
			# Normalizing motion corrected DCE image with mean bias field 
			fslmaths dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz -div dce/mean_dyn_bias_map.nii.gz dce/${PREFIX}_desc-bfc_DCE.nii.gz

			mv dce/dyn_bias.nii.gz dce/${PREFIX}_desc-biases_DCE.nii.gz
			mv dce/mean_dyn_bias_map.nii.gz dce/${PREFIX}_desc-meanbias_DCE.nii.gz
			# remove sampled files
			rm rep_*.nii.gz
		else
			echo Skipping DCE BFC because it already exists...
		fi
	else
		#echo Motion correcting dynamic set
		cp dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz dce/${PREFIX}_desc-bfc_DCE.nii.gz
		# gunzip -f DCE_mc_bfc.nii.gz
	fi
	
	# align existing white matter mask to dynamic images and re-binarize
	# antsApplyTransforms -i T1_wm_mask.nii.gz -r ref_rep.nii -t T1_dyn0GenericAffine.mat -o T1_wm_mask_dyn_pv.nii &> /dev/null
	
	# apply wm mask to all DCE images
	if [ $EN_BIAS1 -eq 1 ]
		then
		fslmaths dce/${PREFIX}_desc-bfc_DCE.nii.gz -mas anat/${PREFIX}_${VFA}_${REF_SPACE}_seg-WM_VFA.nii.gz dce/${PREFIX}_seg-WM_DCE.nii.gz &> /dev/null
	else
		fslmaths $source_dir/dce/${PREFIX}_DCE.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz dce/${PREFIX}_seg-WM_DCE.nii.gz &> /dev/null
	fi

	# normalize dynamic images
	# ------------------------------
	#echo Normalizing dynamic images...
	if [ $EN_Z_NORM -eq 1 ]
		then
		python3 $SCRIPT_PATH/DCE_norm.py $SUBJECT_TP_PATH/dce &> /dev/null
	else
		cp dce/${PREFIX}_desc-bfc_DCE.nii.gz dce/${PREFIX}_desc-bfcz_DCE.nii.gz
	fi
	gzip -f dce/${PREFIX}_desc-bfcz_DCE.nii

	if [ ! -f "dce/${PREFIX}_desc-bfcz_DCE.nii.gz" ]
		then
			echo $source_dir "Missing normalized DCE file." >> $LOG_FILE
			cd $DATA_DIR
			fail=1
			continue
	fi

	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  $prog + .6 / $count" | bc -l)
	echo -ne "SUBJ COMPLETED [==================================================] $prog% ($current/$count) ~$ETA min remaining \r"

	cd $DATA_DIR
	echo $source_dir preprocessing complete! >> $LOG_FILE
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
