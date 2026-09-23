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
USE_PYTHON=0
AIF_SUFFIX="label-AIF_mask"
AIF_TRAINING_SUFFIX="label-AIF_desc-training_mask"
SKIP_IF_SUCCESS=0
SCRIPT_LOOP_DIRS=sub-*/ses-*
AUTOAIF_WEIGHT_PATH="docker/files/model_weight_huber1.h5"
AUTOAIF_MODEL="best"
HD_BET_COMMAND="${HD_BET_COMMAND:-hd-bet}"
AUTO_AIF_PYTHON="${AUTO_AIF_PYTHON:-python3}"
MAX_PARALLEL_JOBS=0
WORKER_WAIT_TIMEOUT_SECONDS="${WORKER_WAIT_TIMEOUT_SECONDS:-7200}"

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
while getopts ":d:bBa:A:ZfhcC:j:mM:sS:tl:w:p" options; do
	case "${options}" in
		a)
			AIF_SUFFIX=${OPTARG}
			;;
		A)
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
			# derivatives dir is up 2 levels from data dir
			DERIV_DIR=$(dirname $(dirname $DATA_DIR))/derivatives
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
			echo "-a: specify AIF suffix (default is 'label-AIF_mask'). .nii.gz will be appended to the suffix."
			echo "-A: enable AutoAIF with argument A (All automatic), M (Manual if available), or T (Manual + Training if available)"
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-c: clean case's derivative folder prior to processing, ensures \"fresh\" runs but cannot use skips"
			echo "-C [name]: enable comparison mode, which will output all files to the specified directory within each timepoint"
			echo "-d [dir_path]: specify BIDS compliant data directory containing all subject folders (sub-*/ses-*/anat|dce/*.nii|*.json)"
			echo "-h: display this message"
			echo "-j [count]: limit concurrent VFA registration and FAST jobs (default is unlimited)"
			echo "-m: enable motion correction"
			echo "-s: skip preprocessing if DCE input file already exists"
			echo "-S [dir_path]: target the subject(s)/session(s) to run (default is 'sub-*/ses-*/')"
			echo "-t: only run up to T1 mapping"
			echo "-w [path]: specify the path to the AutoAIF weights file"
			echo "-M [model]: specify the AutoAIF model name (default is 'best')"
			echo "-p: Use Python for ROCKETSHIP calls"
			echo "-Z: enable Z-slice normalization"
			exit 0
			;;
		l)
			INPUT_LIST=$DATA_DIR/../code/${OPTARG}
			;;
		j)
			if [[ ! "$OPTARG" =~ ^[1-9][0-9]*$ ]]; then
				echo "Invalid argument for -j. Use a positive integer."
				exit 1
			fi
			MAX_PARALLEL_JOBS=$OPTARG
			;;
		m)
			EN_MOTION_CORR=1
			;;
		M)
			AUTOAIF_MODEL=${OPTARG}
			;;
		p)
			USE_PYTHON=1
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

if ! "$HD_BET_COMMAND" --help &> /dev/null; then
	echo "ERROR: HD-BET command '$HD_BET_COMMAND' is unavailable or cannot start. Set HD_BET_COMMAND to a working hd-bet executable." >&2
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
	PREPROCESS_WORKER_DIR="$SCRIPT_PATH/scripts/preprocess"
	GPUFIT_PATH=$(resolve_tool_path "${GPUFIT_PATH:-}" "GpufitCudaAvailableMex.mexa64" "/opt/Gpufit/matlab64")
	GPUFIT_M_PATH=$(resolve_tool_path "${GPUFIT_M_PATH:-}" "ModelID.m" "/opt/Gpufit/matlab")
	if [ -z "$ROCKETSHIP_PATH" ] || [ -z "$GPUFIT_PATH" ] || [ -z "$GPUFIT_M_PATH" ]; then
		echo "ERROR: Unable to locate ROCKETSHIP or GPUfit. Set ROCKETSHIP_PATH, GPUFIT_PATH, and GPUFIT_M_PATH to directories containing their required MATLAB files." >&2
		exit 1
	fi
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
	PREPROCESS_WORKER_DIR="$SCRIPT_PATH/scripts/preprocess"
	GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
fi

if [ $USE_AUTO_AIF -eq 1 ]; then
	AUTO_AIF_PATH=$(resolve_tool_path "${AUTO_AIF_PATH:-}" "main_vif.py" "/opt/vascular_function")
	if [ -z "$AUTO_AIF_PATH" ]; then
		echo "ERROR: Unable to locate AutoAIF. Set AUTO_AIF_PATH to the directory containing main_vif.py." >&2
		exit 1
	fi
	if ! "$AUTO_AIF_PYTHON" -c 'import tensorflow' &> /dev/null; then
		echo "ERROR: AutoAIF Python '$AUTO_AIF_PYTHON' cannot import TensorFlow. Set AUTO_AIF_PYTHON to a TensorFlow-capable interpreter." >&2
		exit 1
	fi
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

wait_for_job_slot() {
	if [ "$MAX_PARALLEL_JOBS" -le 0 ]; then
		return 0
	fi

	while [ "$(jobs -pr | wc -l)" -ge "$MAX_PARALLEL_JOBS" ]; do
		wait -n
	done
}

start_background_job() {
	wait_for_job_slot || return 1
	"$@" &
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
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/test/masks/sub-${pat}_ses-${session_num}_label-AIF_mask.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/test/masks/${pat}_${session_str}_timepoint.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/train/masks/sub-${pat}_ses-${session_num}_label-AIF_mask.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/train/masks/${pat}_${session_str}_timepoint.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
				cp /media/network_mriphysics/USC-PPG/AI_training/loos_model/val/masks/sub-${pat}_ses-${session_num}_label-AIF_mask.nii.gz $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION/dce/${SUBJECT}_${SESSION}_${AIF_TRAINING_SUFFIX}.nii.gz && mask_copied=1
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

	# --- LOCKING FOR MULTI-MACHINE PROCESSING ---
	LOCKFILE="preprocessing_lock.txt"
	LOCKDIR=$(pwd)
	LOCKPATH="$LOCKDIR/$LOCKFILE"
	LOCKHOST=$(hostname)
	LOCKPID=$$
	LOCKLIST="$DERIV_DIR/locks_${LOCKHOST}.txt"
	echo "Attempting to lock $LOCKPATH on $LOCKHOST with PID $LOCKPID"

	# Try to create lock file atomically
	if ( set -o noclobber; echo "$LOCKHOST:$LOCKPID" > "$LOCKPATH" ) 2> /dev/null; then
		echo "$LOCKPATH" >> "$LOCKLIST"
		trap 'for f in $(cat "$LOCKLIST" 2>/dev/null); do rm -f "$f"; done; rm -f "$LOCKLIST"; exit $?' INT TERM EXIT
	else
		echo "Skipping $source_dir because it is currently being processed by $(cat $LOCKPATH)." >> $LOG_FILE
		cd $DERIV_DIR
		continue
	fi

	if [ ! -f $DERIV_DIR/dceprep/$SUBJECT/$SESSION/dce/${PREFIX}_${AIF_SUFFIX}.nii.gz ] && [ ! -f $DERIV_DIR/dceprep/$SUBJECT/$SESSION/dce/${PREFIX}_${AIF_SUFFIX}.nii ] && [ ! -f $DERIV_DIR/dceprep-manualAIF/$SUBJECT/$SESSION/dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz ] && [ $USE_AUTO_AIF -eq 0 ]
		then
		echo "No ${PREFIX}_${AIF_SUFFIX} file found for $DERIV_DIR/dceprep/$SUBJECT/$SESSION/. Skipping timepoint..." >> $LOG_FILE
		cd $DATA_DIR
		continue
	fi

	if [ $SKIP_IF_SUCCESS -eq 1 ]
		then
		if [ -f "dce/${PREFIX}_desc-bfcz_DCE.nii.gz" ] && [ -f "anat/${PREFIX}_space-DCEref_label-brain_mask.nii.gz" ] && \
			[ -f "dce/${PREFIX}_label-AIF_T1map.nii.gz" ] && [ -f "anat/${PREFIX}_space-DCEref_T1map.nii.gz" ] #&& [ -f "reports/${PREFIX}_desc-casereport.html" ]
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
	WORKER_STATUS_DIR="$SUBJECT_TP_PATH/.preprocess_workers"
	rm -rf "$WORKER_STATUS_DIR"
	mkdir -p "$WORKER_STATUS_DIR"
	export source_dir DATA_DIR DERIV_DIR LOG_FILE SUBJECT SESSION PREFIX SUBJECT_TP_PATH SCRIPT_PATH
	export EN_MOTION_CORR EN_BIAS1 EN_BIAS2 EN_Z_NORM USE_AUTO_AIF USE_PYTHON T1_ONLY
	export AIF_SUFFIX AIF_TRAINING_SUFFIX HD_BET_COMMAND AUTO_AIF_PYTHON AUTO_AIF_PATH
	export AUTOAIF_WEIGHT_PATH AUTOAIF_MODEL ROCKETSHIP_PATH GPUFIT_PATH GPUFIT_M_PATH
	export MAX_PARALLEL_JOBS WORKER_STATUS_DIR WORKER_WAIT_TIMEOUT_SECONDS
	# Launch the two workers independently; MAX_PARALLEL_JOBS limits work within each worker.
	bash "$PREPROCESS_WORKER_DIR/preprocess_vfa_t1.sh" &
	vfa_worker_pid=$!
	if [ $T1_ONLY -eq 0 ]
		then
		bash "$PREPROCESS_WORKER_DIR/preprocess_dce_series.sh" &
		dce_worker_pid=$!
	else
		dce_worker_pid=
	fi

	wait "$vfa_worker_pid"
	vfa_worker_status=$?
	if [ -n "$dce_worker_pid" ]
		then
		wait "$dce_worker_pid"
		dce_worker_status=$?
	else
		dce_worker_status=0
	fi

	if [ $vfa_worker_status -ne 0 ] || [ $dce_worker_status -ne 0 ]
		then
		fail=1
		rm -rf "$WORKER_STATUS_DIR"
		cd "$DATA_DIR" || exit 1
		continue
	fi

	ETA=$(echo "scale=0;  $mETA - ($SECONDS)/60" | bc -l)
	prog=$(echo "scale=2;  100 * $current / $count" | bc -l)
	echo -ne "SUBJ COMPLETED [==================================================] $prog% ($current/$count) ~$ETA min remaining \r"
	rm -rf "$WORKER_STATUS_DIR"
	cd "$DATA_DIR" || exit 1
	echo "$source_dir preprocessing complete!" >> "$LOG_FILE"
	let successes++
	continue

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
