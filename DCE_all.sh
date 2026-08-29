#!/bin/bash
# FSL, Matlab, ROCKETSHIP + parametric_scripts, ANTS, and Python are required
# Within ROCKETSHIP/parametric_scripts should be a custom scripts folder with T1mapping_fit.m
shopt -s extglob
# control variables
COMPARISON_MODE=0
EN_BIAS1=0
EN_SMOOTHING=0
fail=0
count=0
total=0
successes=0
SKIP_IF_SUCCESS=0
USE_FREESURFER=0
PURGE_INTERMEDIATES=0
GIGA_PURGE=0
TARGET_FLAG=0
SCRIPT_LOOP_DIR=dceprep/sub-*/ses-*
USE_PYTHON=0

# options
while getopts ":d:C:fhl:sST:p" options; do
	case "${options}" in
		b)
			EN_BIAS1=1
			;;
		C)
			COMPARISON_MODE=1
			OUTPUT_DIR=${OPTARG}
			SCRIPT_LOOP_DIR=dceprep-${OPTARG}/sub-*/ses-*
			;;
		d)
			DATA_DIR=${OPTARG}
			if [ ${DATA_DIR::-1} == "/" ]
				then
				DATA_DIR=${DATA_DIR::-1}
			fi
			date=$(date +%Y-%m-%d)
			DERIV_DIR=$(dirname $(dirname $DATA_DIR))/derivatives
			LOG_FILE=$DERIV_DIR/logs/dce_log_$date.txt
			if [ ! -d "$DATA_DIR/logs" ]
				then
				mkdir $DATA_DIR/logs
			fi
			# write command to log file
			echo "Command: $0 $@" > $LOG_FILE
			;;
		f)
			USE_FREESURFER=1
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, processing every folder ending in '_timepoint'."
			echo "The data must be preprocessed with \`preprocess_all.sh\` before running this script."
			echo "The input is \`DCE_bfc_norm.nii.gz\`. The output is mainly the DCE outputs (Ktrans maps) and QC reports."
			echo "If everything goes well, the script will output a case report for each subject and a population report for the entire dataset."
			echo "-C: enable comparison mode. Specify output directory."
			echo "-d: specify main data directory containing all subject folders"
			echo "-f: enable Freesurfer wm parcellation for subregion analysis"
			echo "-h: display this message"
			echo "-p: use Python for ROCKETSHIP calls"
			# echo "-l: specify a list of subjects to process (filename only, place in code folder)"
			echo "-s: skip subjects that have already been processed"
			echo "-S: enable smoothing of DCE input"
			echo "-T [dir_path]: specify the subject(s)/session(s) to run (default is 'sub-*/ses-*/')"
			exit 0
			;;
		l)
			INPUT_LIST=$DATA_DIR/../code/${OPTARG}
			;;
		p)
			USE_PYTHON=1
			;;
		s)
			SKIP_IF_SUCCESS=1
			;;
		S)
			EN_SMOOTHING=1
			;;
		T)
			TARGET_FLAG=1
			if [ $COMPARISON_MODE -eq 1 ]
				then
				SCRIPT_LOOP_DIR=dceprep-$OUTPUT_DIR/$OPTARG
			else
				SCRIPT_LOOP_DIR=dceprep/$OPTARG
			fi
			echo "Processing target directory: $SCRIPT_LOOP_DIR"
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

resolve_tool_path() {
	local configured_path=$1
	local marker_file=$2
	shift 2
	local candidate_path

	if [ -n "$configured_path" ]; then
		if [ -f "$configured_path/$marker_file" ]; then
			printf '%s\n' "$configured_path"
			return 0
		fi
		echo "ERROR: Configured path $configured_path does not contain $marker_file." >&2
		return 1
	fi

	for candidate_path in "$@"; do
		if [ -f "$candidate_path/$marker_file" ]; then
			printf '%s\n' "$candidate_path"
			return 0
		fi
	done

	find "$HOME" \
		\( -path "$HOME/.local/share/Trash" -o -path "$HOME/.local/share/Trash/*" -o -path "$HOME/.Trash" -o -path "$HOME/.Trash/*" \) -prune -o \
		-type f -name "$marker_file" -printf '%h\n' -quit 2> /dev/null
}

if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(resolve_tool_path "${ROCKETSHIP_PATH:-}" "run_dce_cli.m" "/opt/ROCKETSHIP/ROCKETSHIP-dev")
	SCRIPT_PATH=$(dirname "$(realpath $0)")
	GPUFIT_PATH=$(resolve_tool_path "${GPUFIT_PATH:-}" "GpufitConstrainedMex.mexa64" "/opt/Gpufit/matlab64")
	GPUFIT_M_PATH=$(resolve_tool_path "${GPUFIT_M_PATH:-}" "ModelID.m" "/opt/Gpufit/matlab")
	if [ -z "$ROCKETSHIP_PATH" ] || [ -z "$GPUFIT_PATH" ] || [ -z "$GPUFIT_M_PATH" ]; then
		echo "ERROR: Unable to locate ROCKETSHIP or GPUfit. Set ROCKETSHIP_PATH, GPUFIT_PATH, and GPUFIT_M_PATH to directories containing their required MATLAB files." >&2
		exit 1
	fi
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
	GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
fi
cd $DERIV_DIR || exit 1

# rm dce_log.txt
# read list of subjects
# while IFS= read -r line; do
# 	SUBJECT=sub-$(echo $line | awk '{print $1}')
# 	echo $SUBJECT
# 	SESSION=$(echo $line | awk '{print $3}')
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
    echo -ne "Progress: $((elapsed_time * 100 / estimated_total_time))% - Elapsed time: $(($elapsed_time / 60))m $(($elapsed_time % 60))s - "
	if [ $remaining_time -lt 0 ]
		then
		echo -ne "Estimated remaining time: calculating...                    \r"
	else
    	echo -ne "Estimated remaining time: $(($remaining_time / 60))m $(($remaining_time % 60))s                     \r"
	fi
}
# if [ $COMPARISON_MODE -eq 1 ] && [ -d dceprep-$OUTPUT_DIR ] && [ $TARGET_FLAG -eq 0 ];
# 	then
# 	SCRIPT_LOOP_DIR=dceprep-$OUTPUT_DIR/sub-*/ses-*
# elif [ $COMPARISON_MODE -eq 1 ] && [ -d dceprep-$OUTPUT_DIR ] && [ $TARGET_FLAG -eq 0 ];
# 	then
# 	SCRIPT_LOOP_DIR=dceprep/sub-*/ses-*
# fi
# if [ -z "$(ls -A $SCRIPT_LOOP_DIR 2>/dev/null)" ]; then
# 		SCRIPT_LOOP_DIR=dceprep-multihance_fix/sub-*/ses-*
# fi
for der_dir in $SCRIPT_LOOP_DIR; do
	((total++))
done
runtime=70
start_time=$(date +%s)
for der_dir in $SCRIPT_LOOP_DIR; do
	dir=$der_dir
	date >> $LOG_FILE

	((count++))
	show_progress $count $start_time $total $runtime

	# get subject ID and session
	SUBJECT=$(echo $der_dir | grep -o 'sub-[^/]*')
	SESSION=$(echo $der_dir | grep -o 'ses-[0-9]*')
	PREFIX=${SUBJECT}_${SESSION}
	if [ $COMPARISON_MODE -eq 1 ]
		then
		echo "Comparison mode enabled. Processing in $OUTPUT_DIR..." >> $LOG_FILE
		if [ ! -d $DERIV_DIR/dceprep-"$OUTPUT_DIR"/$SUBJECT/$SESSION ]
			then
			mkdir -p $DERIV_DIR/dceprep-"$OUTPUT_DIR"/$SUBJECT/$SESSION
			mkdir -p $DERIV_DIR/dceprep-"$OUTPUT_DIR"/$SUBJECT/$SESSION/dce
			mkdir -p $DERIV_DIR/dceprep-"$OUTPUT_DIR"/$SUBJECT/$SESSION/anat
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/dce/*bfcz* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/dce/*desc-AIF*_T1map* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/dce/*hmc* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/dce/*.txt $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/anat/*_T1map* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/anat
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/anat/*mask* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/anat
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/anat/*.mat $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/anat
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/anat/*wmparc* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/anat
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/anat/*DCEref_VFA* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/anat
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/anat/*DCEref_T1w* $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/anat
			cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/figures $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/figures
		fi
		cd $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION || echo "ERROR: $OUTPUT_DIR does not exist. Preprocess first or check the name and try again." >> $LOG_FILE
		if [ ! -f dce/${PREFIX}_desc-hmc_DCEref.nii.gz ]
			then
			# probably a no motion correction run, get 2nd t-slice of DCE
			# cp dce/${PREFIX}_desc-bfc_DCE.nii.gz dce/${PREFIX}_desc-hmc_DCE.nii.gz
			fslmerge -n 1 dce/${PREFIX}_desc-hmc_DCEref.nii.gz dce/${PREFIX}_desc-bfc_DCE.nii.gz
		fi
	else
		cd $der_dir || echo "ERROR: $der_dir does not exist. Preprocess first or check the name and try again." >> $LOG_FILE
	fi
	SUBJECT_TP_PATH=$(pwd)
	if [ ! -f anat/${PREFIX}_label-brain_T1w.nii.gz ]
		then
		cp -r $DERIV_DIR/dceprep-multihance_fix/$SUBJECT/$SESSION/anat/${PREFIX}_label-brain_T1w.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/anat
	fi
	# Locking mechanism to prevent concurrent processing from other machines
	LOCKFILE="lock.txt"
	LOCKDIR=$(pwd)
	LOCKPATH="$LOCKDIR/$LOCKFILE"
	LOCKHOST=$(hostname)
	LOCKPID=$$
	LOCKLIST="$DERIV_DIR/locks_${LOCKHOST}.txt"
	echo "Locking $LOCKPATH on $LOCKHOST with PID $LOCKPID"

	# Try to create lock file atomically
	if ( set -o noclobber; echo "$LOCKHOST:$LOCKPID" > "$LOCKPATH" ) 2> /dev/null; then
		echo "$LOCKPATH" >> "$LOCKLIST"
		trap 'for f in $(cat "$LOCKLIST" 2>/dev/null); do rm -f "$f"; done; rm -f "$LOCKLIST"; exit $?' INT TERM EXIT
	else
		echo "Skipping $dir because it is currently being processed by $(cat $LOCKPATH)." >> $LOG_FILE
		cd $DERIV_DIR
		continue
	fi
	if [ $SKIP_IF_SUCCESS -eq 1 ]
		then
		if [ -f "reports/${PREFIX}_desc-casereport.html" ] && [ -f "anat/${PREFIX}_space-DCEref_seg-wmparc_dseg.nii.gz" ]
			then
			echo "Skipping $dir because it has already been processed." >> $LOG_FILE
			((successes++))
			if [ $PURGE_INTERMEDIATES -eq 1 ] # && [ $COMPARISON_MODE -eq 1 ]
				then
				cd anat
				rm -f !(${PREFIX}*bfczunified_VFA.nii|${PREFIX}_space-DCEref_T1map*|${PREFIX}*label-*_T1map*|*.mat|*wmparc.nii.gz|*space-DCEref_label-brain_mask.nii.gz)
				cd ../dce
				rm -f !(${PREFIX}*Ktrans*|${PREFIX}*bfcz_DCE*|${PREFIX}*AIFincluded*|${PREFIX}*AIF_T1map*|figures|*.log|*.txt|*.par)
			fi
			cd $DERIV_DIR
			continue
		fi
	fi
	if [ ! -f "dce/${PREFIX}_desc-bfcz_DCE.nii.gz" ] && [ ! -f "dce/${PREFIX}_desc-bfcz_DCE.nii" ]
		then
		echo Missing input file dce/${PREFIX}_desc-bfcz_DCE. Make sure the data has been preprocessed. Skipping $dir... >> $LOG_FILE
		cd $DERIV_DIR
		fail=1
		continue
	fi

	# iNESMA smooth DCE input (exclude AIF roi)
	if [ $EN_SMOOTHING -eq 1 ]
		then
		python3 $SCRIPT_PATH/iNESMA_GPU.py $PREFIX dce/${PREFIX}_desc-bfcz_DCE.nii.gz dce/${PREFIX}_desc-AIF_T1map.nii.gz
	fi
	
	# DCE
	# ------------------------------
	# echo Begin DCE processing...
	rm -f dce/dce_patlak_fit_rois.xls
	if [ $USE_PYTHON -eq 1 ]
		then
		${ROCKETSHIP_PATH}/.venv/bin/python ${ROCKETSHIP_PATH}/run_dce_python_case.py --subject-source "$DATA_DIR/$SUBJECT/$SESSION/" --subject-tp $SUBJECT_TP_PATH --output-dir $SUBJECT_TP_PATH --events off
	else
		matlab -nodisplay -r "cd('$ROCKETSHIP_PATH'); addpath '$GPUFIT_PATH'; addpath '$GPUFIT_M_PATH'; run_dce_cli('$DATA_DIR/$SUBJECT/$SESSION/', '$SUBJECT_TP_PATH/'); exit;"
	fi
	gzip dce/*.nii
	mv dce/*_fit_*trans.nii.gz dce/${PREFIX}_Ktrans.nii.gz
	mv dce/*_fit_*trans_ci_low.nii.gz dce/${PREFIX}_desc-cilow_Ktrans.nii.gz
	mv dce/*_fit_*trans_ci_high.nii.gz dce/${PREFIX}_desc-cihigh_Ktrans.nii.gz
	mv dce/*_fit_vp.nii.gz dce/${PREFIX}_vp.nii.gz
	mv dce/*_fit_vp_ci_low.nii.gz dce/${PREFIX}_desc-cilow_vp.nii.gz
	mv dce/*_fit_vp_ci_high.nii.gz dce/${PREFIX}_desc-cihigh_vp.nii.gz
	mv dce/*_fit_sse.nii.gz dce/${PREFIX}_sse.nii.gz
	# move images into figures folder
	mv dce/dce*.png figures/
	rm -f dce/*.fig
	if [ ! -f "dce/${PREFIX}_Ktrans.nii" ]
		then
			echo $dir "Missing Ktrans maps. DCE failed or inputs were not generated. Hopefully message below is relevant." >> $LOG_FILE
			tail -1 dce/A_dceR1info.log >> $LOG_FILE
			cd $DATA_DIR/../derivatives
			fail=1
			continue
	fi
	
	# Analyze results
	# ------------------------------
	
	# Align then re-binarize gm mask
	DCEREF_FILE=$(ls dce/${PREFIX}*DCEref.nii.gz | head -n 1)
	antsApplyTransforms -i anat/${PREFIX}_label-GM_mask.nii.gz -r $DCEREF_FILE -t anat/${PREFIX}_from-T1w_to-DCEref.mat -o anat/${PREFIX}_space-DCEref_label-GM_mask_pv.nii.gz &> /dev/null
	fslmaths anat/${PREFIX}_space-DCEref_label-GM_mask_pv.nii.gz -thr 0.9 -bin anat/${PREFIX}_space-DCEref_label-GM_mask.nii.gz
	rm anat/${PREFIX}_space-DCEref_label-GM_mask_pv.nii.gz

	# Align CSF mask
	antsApplyTransforms -i anat/${PREFIX}_label-CSF_mask.nii.gz -r $DCEREF_FILE -t anat/${PREFIX}_from-T1w_to-DCEref.mat -o anat/${PREFIX}_space-DCEref_label-CSF_mask_pv.nii.gz &> /dev/null
	fslmaths anat/${PREFIX}_space-DCEref_label-CSF_mask_pv.nii.gz -thr 0.9 -bin anat/${PREFIX}_space-DCEref_label-CSF_mask.nii.gz
	rm anat/${PREFIX}_space-DCEref_label-CSF_mask_pv.nii.gz

	# Apply masks to T1 map
	fslmaths anat/${PREFIX}_space-DCEref_T1map.nii  -mas anat/${PREFIX}_space-DCEref_label-WM_mask.nii.gz anat/${PREFIX}_space-DCEref_label-WM_T1map.nii
	fslmaths anat/${PREFIX}_space-DCEref_T1map.nii -mas anat/${PREFIX}_space-DCEref_label-GM_mask.nii.gz anat/${PREFIX}_space-DCEref_label-GM_T1map.nii
	fslmaths anat/${PREFIX}_space-DCEref_T1map.nii -mas anat/${PREFIX}_space-DCEref_label-CSF_mask.nii.gz anat/${PREFIX}_space-DCEref_label-CSF_T1map.nii

	# Apply masks to Ktrans map
	fslmaths dce/${PREFIX}_Ktrans.nii -mas anat/${PREFIX}_space-DCEref_label-WM_mask.nii.gz dce/${PREFIX}_label-WM_Ktrans.nii
	fslmaths dce/${PREFIX}_Ktrans.nii -mas anat/${PREFIX}_space-DCEref_label-GM_mask.nii.gz dce/${PREFIX}_label-GM_Ktrans.nii
	fslmaths dce/${PREFIX}_Ktrans.nii -mas anat/${PREFIX}_space-DCEref_label-CSF_mask.nii.gz dce/${PREFIX}_label-CSF_Ktrans.nii

	# registration QC
	python3 $SCRIPT_PATH/ktrans_analysis.py $dir $PREFIX

	fslmaths anat/${PREFIX}_space-DCEref_label-WM_mask.nii.gz -add 2000 huh.nii
	fslmaths huh.nii.gz -thr 2001 huh.nii
	fslmaths $DCEREF_FILE -sub huh.nii.gz bozo.nii
	fslmaths bozo.nii -thr 0 anat/${PREFIX}_space-DCEref_label-WMQC.nii.gz
	
	fslmaths anat/${PREFIX}_space-DCEref_label-GM_mask.nii.gz -add 2000 huh2.nii
	fslmaths huh2.nii.gz -thr 2001 huh2.nii
	fslmaths $DCEREF_FILE -sub huh2.nii.gz bozo2.nii
	fslmaths bozo2.nii -thr 0 anat/${PREFIX}_space-DCEref_label-GMQC.nii.gz
	rm huh.nii.gz huh2.nii.gz bozo.nii.gz bozo2.nii.gz
	# wm parcellation with Freesurfer
	if [ $USE_FREESURFER -eq 1 ]
		then
		# get subject ID
		subj=$(echo $dir | rev | cut -d'/' -f2 | rev)

		# run Freesurfer
		# if [ ! -f $dir/freesurfer/$SUBJECT/$SESSION/mri/wmparc.mgz ]
		# 	then
		# 	mkdir -p $dir/freesurfer/$SUBJECT/$SESSION
		# 	recon-all -s $DATA_DIR -i anat/${PREFIX}_T1w.nii.gz -sd $dir/freesurfer/$SUBJECT/$SESSION -all -parallel -openmp 8
		# fi

		# get wm parcellation
		mri_label2vol --seg $DERIV_DIR/freesurfer/$SUBJECT/$SESSION/mri/wmparc.mgz \
			--temp $DERIV_DIR/freesurfer/$SUBJECT/$SESSION/mri/rawavg.mgz \
			--o $DERIV_DIR/freesurfer/$SUBJECT/$SESSION/mri/wmparc-in-rawavg.mgz \
			--regheader $DERIV_DIR/freesurfer/$SUBJECT/$SESSION/mri/wmparc.mgz &> /dev/null
        mri_convert $DERIV_DIR/freesurfer/$SUBJECT/$SESSION/mri/wmparc-in-rawavg.mgz wmparc.nii.gz &> /dev/null
        antsApplyTransforms -i wmparc.nii.gz -r dce/${PREFIX}_desc-hmc_DCEref.nii.gz -t anat/${PREFIX}_from-t1w_to-DCEref.mat -n NearestNeighbor -o anat/${PREFIX}_space-DCEref_seg-wmparc_dseg.nii &> /dev/null
        gzip -f anat/${PREFIX}_space-DCEref_seg-wmparc_dseg.nii &> /dev/null
		rm wmparc.nii.gz
	elif [ ! -f dce/${PREFIX}_space-MNI_Ktrans.nii.gz ]
		then
		# flirt -in DCE_mc.nii.gz -ref $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz -omat DCE2MNI.mat -out DCE_MNI_FSL.nii.gz
		# flirt -in $dir/T1.nii -ref $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz -out t1w_MNI.nii.gz
		# antsRegistration --verbose 0 --dimensionality 3 --float 0 --collapse-output-transforms 1 \
		# 	--output [ DCE_MPRAGE,DCE_MPRAGE.nii.gz ] --interpolation Linear --use-histogram-matching 0 \
		# 	--winsorize-image-intensities [ 0.005,0.995 ] --transform Affine[ 0.1 ] \
		# 	--metric MI[ T1_bet.nii.gz,DCE_mc.nii.gz,1,32,Regular,0.25 ] \
		# 	--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
		# antsRegistrationSyNQuick.sh -d 3 -f anat/${PREFIX}_label-brain_T1w.nii.gz -m dce/${PREFIX}_desc-hmc_DCEref.nii.gz -o dce/${PREFIX}_space-MNI_DCEref -n 8
		antsRegistrationSyNQuick.sh -d 3 -f $FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz -m anat/${PREFIX}_label-brain_T1w.nii.gz -o anat/${PREFIX}_space-MNI_T1w -n 8
		# antsApplyTransforms -i dce/${PREFIX}_desc-hmc_DCEref.nii.gz -r $FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz -t dce/${PREFIX}_space-MNI_DCEref1Warp.nii.gz -t anat/${PREFIX}_space-MNI_T1w0GenericAffine.mat -t [ anat/${PREFIX}_from-T1w_to-DCEref.mat, 1] -o DCE_mc_MNI.nii.gz
		antsApplyTransforms -i dce/${PREFIX}_desc-hmc_DCEref.nii.gz -r $FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz -t anat/${PREFIX}_space-MNI_T1w0GenericAffine.mat -t [ anat/${PREFIX}_from-T1w_to-DCEref.mat, 1] -o dce/${PREFIX}_space-MNI_DCEref.nii.gz
		# antsRegistration --verbose 1 --dimensionality 3 --float 0 --collapse-output-transforms 1 \
		# 	--output [ anat/${PREFIX}_space-MNI,anat/${PREFIX}_space-MNI_T1w.nii.gz ] --interpolation Linear --use-histogram-matching 0 \
		# 	--winsorize-image-intensities [ 0.005,0.995 ] --transform SyN[ 0.1 ] \
		# 	--metric MI[ $FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz,anat/${PREFIX}_space-DCEref_T1w.nii.gz,1,32,Regular,0.25 ] \
		# 	--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
		# antsApplyTransforms -i dce/${PREFIX}_Ktrans.nii -r $FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz -t ${PREFIX}_space-MNI_T1w0Warp.nii.gz -t t1w_MNI0GenericAffine.mat -t [T1_dyn0GenericAffine.mat, 1] -o Ktrans_MNI.nii.gz
		antsApplyTransforms -i dce/${PREFIX}_Ktrans.nii -r $FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz -t anat/${PREFIX}_space-MNI_T1w0GenericAffine.mat -t [ anat/${PREFIX}_from-T1w_to-DCEref.mat, 1] -o dce/${PREFIX}_space-MNI_Ktrans.nii.gz
		# antsApplyTransforms -i dce_patlak_fit_vp.nii -r $FSLDIR/data/standard/MNI152_T1_1mm_brain.nii.gz -t t1w_MNI1Warp.nii.gz -t t1w_MNI0GenericAffine.mat -t [T1_dyn0GenericAffine.mat, 1] -o vp_MNI.nii.gz
		# flirt -in dce_patlak_fit_Ktrans.nii -ref $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz -out ktrans_2_MNI.nii.gz -init DCE2MNI.mat -applyxfm
	else
		echo SKIP
	fi
	mkdir reports &> /dev/null
	python3 $SCRIPT_PATH/case_report.py $DATA_DIR/$SUBJECT/$SESSION $PREFIX $USE_FREESURFER
	python3 $SCRIPT_PATH/ktrans_report.py $DATA_DIR/$SUBJECT/$SESSION $PREFIX

	if [ $PURGE_INTERMEDIATES -eq 1 ]
		then
		# rm -f !(Ktrans_*|T1_gm*|T1_wm*|T1_csf*|*_patlak_fit*.nii|case_report.html|*_MNI.nii.gz|*fit_VFA.nii|figures|dce*.png|*.log)
		cd anat
		rm -f !(${PREFIX}*bfczunified_VFA.nii|${PREFIX}_space-DCEref_T1map*|${PREFIX}*label-*_T1map*|*.mat|*wmparc.nii.gz)
		cd ../dce
		rm -f !(${PREFIX}*Ktrans*|${PREFIX}*bfcz_DCE*|${PREFIX}*AIFincluded*|${PREFIX}*AIF_T1map*|figures|*.log|*.txt|*.par)
	elif [ $GIGA_PURGE -eq 1 ]
		then
		rm -f !(case_report.html|figures|*.log)
	fi
	cd $DERIV_DIR
	echo $dir processing complete! >> $LOG_FILE
	((successes++))
done # < $INPUT_LIST

mkdir -p $DERIV_DIR/reports
python3 $SCRIPT_PATH/population_report.py $DERIV_DIR $OUTPUT_DIR $ROCKETSHIP_PATH
((failures=count-successes))
echo "Completed DCE processing for $count subjects." >> $LOG_FILE
echo $successes subjects succeeded >> $LOG_FILE
echo $failures subjects failed >> $LOG_FILE

if [ $fail -eq 1 ]
	then
	exit 1
fi
