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
successes=0
processed=0
processed_seconds=0
session_ran=0
session_start=0

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

# Importing torch / TensorFlow takes ~2 s each, so these checks run alongside path discovery
"$HD_BET_COMMAND" --help &> /dev/null &
hd_bet_check_pid=$!
if [ $USE_AUTO_AIF -eq 1 ]; then
	"$AUTO_AIF_PYTHON" -c 'import tensorflow' &> /dev/null &
	tensorflow_check_pid=$!
fi

# Every tool marker file under $HOME, as "name<TAB>dir" lines in find's order. Filled by
# the first lookup that needs it: one pass serves all tools (a pass each cost ~1.3 s).
HOME_MARKER_FILES=
HOME_MARKER_FILES_SEARCHED=0
HOME_MARKER_NAMES=(run_dce_cli.m GpufitCudaAvailableMex.mexa64 ModelID.m main_vif.py)

# Set variable $1 to the directory holding marker file $3: configured path $2 if given,
# else the first of the remaining default paths that has it, else the first match under $HOME
resolve_tool_path() {
	local -n resolved_path=$1
	local configured_path=$2
	local marker_file=$3
	shift 3
	local candidate_path name_args=() marker_name

	resolved_path=
	if [ -n "$configured_path" ]; then
		if [ -f "$configured_path/$marker_file" ]; then
			resolved_path=$configured_path
			return 0
		fi
		echo "ERROR: Configured path $configured_path does not contain $marker_file." >&2
		return 1
	fi

	for candidate_path in "$@"; do
		if [ -f "$candidate_path/$marker_file" ]; then
			resolved_path=$candidate_path
			return 0
		fi
	done

	if [ $HOME_MARKER_FILES_SEARCHED -eq 0 ]; then
		for marker_name in "${HOME_MARKER_NAMES[@]}"; do
			name_args+=(-o -name "$marker_name")
		done
		HOME_MARKER_FILES=$(find "$HOME" \
			\( -path "$HOME/.local/share/Trash" -o -path "$HOME/.local/share/Trash/*" -o -path "$HOME/.Trash" -o -path "$HOME/.Trash/*" \) -prune -o \
			-type f \( "${name_args[@]:1}" \) -printf '%f\t%h\n' 2> /dev/null)
		HOME_MARKER_FILES_SEARCHED=1
	fi
	resolved_path=$(awk -F '\t' -v marker="$marker_file" '$1 == marker { print $2; exit }' <<< "$HOME_MARKER_FILES")
}

if [[ "$OSTYPE" == "linux-gnu" ]]; then
	resolve_tool_path ROCKETSHIP_PATH "${ROCKETSHIP_PATH:-}" "run_dce_cli.m" "/opt/ROCKETSHIP/ROCKETSHIP-dev"
	SCRIPT_PATH=$(dirname "$(realpath $0)")
	PREPROCESS_WORKER_DIR="$SCRIPT_PATH/scripts/preprocess"
	# the Gpufit MATLAB bindings are only used by the MATLAB ROCKETSHIP calls
	if [ $USE_PYTHON -eq 0 ]; then
		resolve_tool_path GPUFIT_PATH "${GPUFIT_PATH:-}" "GpufitCudaAvailableMex.mexa64" "/opt/Gpufit/matlab64"
		resolve_tool_path GPUFIT_M_PATH "${GPUFIT_M_PATH:-}" "ModelID.m" "/opt/Gpufit/matlab"
	fi
	if [ -z "$ROCKETSHIP_PATH" ] || { [ $USE_PYTHON -eq 0 ] && { [ -z "$GPUFIT_PATH" ] || [ -z "$GPUFIT_M_PATH" ]; }; }; then
		echo "ERROR: Unable to locate ROCKETSHIP or GPUfit. Set ROCKETSHIP_PATH, GPUFIT_PATH, and GPUFIT_M_PATH to directories containing their required MATLAB files." >&2
		exit 1
	fi
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
	PREPROCESS_WORKER_DIR="$SCRIPT_PATH/scripts/preprocess"
	GPUFIT_PATH=$(find $HOME -type d -name Gpufit-build)
fi

if ! wait "$hd_bet_check_pid"; then
	echo "ERROR: HD-BET command '$HD_BET_COMMAND' is unavailable or cannot start. Set HD_BET_COMMAND to a working hd-bet executable." >&2
	exit 1
fi

if [ $USE_AUTO_AIF -eq 1 ]; then
	resolve_tool_path AUTO_AIF_PATH "${AUTO_AIF_PATH:-}" "main_vif.py" "/opt/vascular_function"
	if [ -z "$AUTO_AIF_PATH" ]; then
		echo "ERROR: Unable to locate AutoAIF. Set AUTO_AIF_PATH to the directory containing main_vif.py." >&2
		exit 1
	fi
	if ! wait "$tensorflow_check_pid"; then
		echo "ERROR: AutoAIF Python '$AUTO_AIF_PYTHON' cannot import TensorFlow. Set AUTO_AIF_PYTHON to a TensorFlow-capable interpreter." >&2
		exit 1
	fi
fi
cd $DATA_DIR || exit 1

source "$SCRIPT_PATH/scripts/session_lock.sh"
install_session_cleanup

# count timepoints
for source_dir in $DATA_DIR/$SCRIPT_LOOP_DIRS; do
	((count++))
done
# Redraw the progress line in place on a terminal; print one line per update otherwise
if [ -t 1 ]; then
	PROGRESS_PREFIX='\r\033[K'
	PROGRESS_SUFFIX=''
else
	PROGRESS_PREFIX=''
	PROGRESS_SUFFIX='\n'
fi

format_duration() {
	local seconds=$1
	if [ $seconds -ge 3600 ]; then
		printf '%dh%02dm' $((seconds / 3600)) $((seconds % 3600 / 60))
	else
		printf '%dm%02ds' $((seconds / 60)) $((seconds % 60))
	fi
}

# Add the last session's runtime to the ETA average (only sessions whose workers ran,
# since skipped/already-processed sessions finish instantly and would skew it)
record_session_time() {
	if [ $session_ran -eq 1 ]; then
		((processed++))
		((processed_seconds += SECONDS - session_start))
		session_ran=0
	fi
}

show_progress() {
	local done=$1
	local label=$2
	local width=20
	local filled=$((count > 0 ? done * width / count : width))
	local percent=$((count > 0 ? done * 100 / count : 100))
	local bar eta="--"
	bar=$(printf '%*s' $filled '' | tr ' ' '=')$(printf '%*s' $((width - filled)) '')
	if [ $processed -gt 0 ] && [ $done -lt $count ]; then
		eta="~$(format_duration $((processed_seconds / processed * (count - done))))"
	fi
	local line
	printf -v line "[%s] %d/%d (%d%%) | %s | ok %d, failed %d, skipped %d | elapsed %s | ETA %s" \
		"$bar" $done $count $percent "$label" $successes $failures $((done - successes - failures)) \
		"$(format_duration $SECONDS)" "$eta"
	# A wrapped line can't be redrawn in place, so fit it to the terminal
	if [ -t 1 ]; then
		local cols
		cols=$(tput cols 2> /dev/null || echo 80)
		line=${line:0:$((cols - 1))}
	fi
	printf "${PROGRESS_PREFIX}%s${PROGRESS_SUFFIX}" "$line"
}

# Step label a worker last reported via set_worker_step
worker_step() {
	if [ -f "$WORKER_STATUS_DIR/$1.done" ]; then
		echo "done"
	elif [ -f "$WORKER_STATUS_DIR/$1.failed" ]; then
		echo "FAILED"
	else
		cat "$WORKER_STATUS_DIR/$1.step" 2> /dev/null || echo "starting"
	fi
}

# Redraw the progress line with each worker's step while either is running.
# Off a terminal, only print when a step changes.
watch_workers() {
	local spinner='|/-\' tick=0 status last_status=""
	while kill -0 "$vfa_worker_pid" 2> /dev/null || { [ -n "$dce_worker_pid" ] && kill -0 "$dce_worker_pid" 2> /dev/null; }; do
		status="$SUBJECT/$SESSION | T1: $(worker_step vfa_t1)"
		[ -n "$dce_worker_pid" ] && status+=" | DCE: $(worker_step dce)"
		if [ -t 1 ]; then
			show_progress $((current - 1)) "${spinner:tick++ % 4:1} $status ($(format_duration $((SECONDS - session_start))))"
		elif [ "$status" != "$last_status" ]; then
			show_progress $((current - 1)) "$status"
			last_status=$status
		fi
		sleep 1
	done
}

# Print each failed worker's reason below the progress line so failures are visible
# without opening the log. Workers that died without a reason point at their log.
report_worker_failures() {
	local worker reason status
	[ -t 1 ] && echo
	for worker in vfa_t1 dce; do
		status=$vfa_worker_status
		[ "$worker" = dce ] && status=$dce_worker_status
		if [ -s "$WORKER_STATUS_DIR/$worker.failed" ]; then
			reason=$(cat "$WORKER_STATUS_DIR/$worker.failed")
		elif [ "$status" -ne 0 ]; then
			reason="exited unexpectedly"
			echo "$SUBJECT/$SESSION $worker worker $reason. See $SUBJECT_TP_PATH/logs/${PREFIX}_preprocess_$worker.log" >> "$LOG_FILE"
		else
			continue
		fi
		echo "FAILED $SUBJECT/$SESSION [$worker]: ${reason#$source_dir }" >&2
		echo "  log: $SUBJECT_TP_PATH/logs/${PREFIX}_preprocess_$worker.log" >&2
	done
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
	if [ ${source_dir::-1} == "/" ]; then
		source_dir=$DATA_DIR/${source_dir::-1}
	fi
	release_session_lock
	record_session_time
	show_progress $current "$(echo $source_dir | grep -o 'sub-[^/]*/ses-[^/]*')"
	date >> $LOG_FILE
	echo "Preprocessing ${source_dir}..." >> $LOG_FILE
	((current++))

	# get subject ID and session
	SUBJECT=$(echo $source_dir | grep -o 'sub-[^/]*')
	SESSION=$(echo $source_dir | grep -o 'ses-[0-9]*')
	PREFIX=${SUBJECT}_${SESSION}

	if [ $COMPARISON_MODE -eq 1 ]
		then
		SUBJECT_TP_PATH=$DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION
		if [ ! -d "$SUBJECT_TP_PATH" ]
			then
			echo "Comparison mode enabled. Creating output directory $OUTPUT_DIR..." >> $LOG_FILE
		fi
	else
		SUBJECT_TP_PATH=$DERIV_DIR/dceprep/$SUBJECT/$SESSION
	fi
	mkdir -p "$SUBJECT_TP_PATH/dce"
	cd "$SUBJECT_TP_PATH" || exit 1
	SUBJECT_TP_PATH=$(pwd)

	# Lock before writing anything so other machines skip this session
	if ! acquire_session_lock "$SUBJECT_TP_PATH"
		then
		cd $DATA_DIR
		continue
	fi

	if [ $COMPARISON_MODE -eq 1 ]
		then
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
				release_session_lock
				rm -rf $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT/$SESSION
				if [ -z "$(ls -A $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT)" ]
					then
					rm -rf $DERIV_DIR/dceprep-$OUTPUT_DIR/$SUBJECT
				fi
				cd $DATA_DIR
				continue
			fi
		fi
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

	# A scanner-provided T1 map replaces the VFA fitting
	T1MAP_PROVIDED=0
	[ -f "$source_dir/anat/${PREFIX}_T1map.nii.gz" ] && T1MAP_PROVIDED=1

	# get list of VFAs and sort them
	VFA_LIST=($(ls $source_dir/anat/*.nii* | grep -v "$source_dir/anat/*T1w.nii*" | grep -v "$source_dir/anat/*T1map.nii*" | grep -v "$source_dir/dce/*aif.nii*"))
	VFA_LIST=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o -E 'flip-[0-9]+' | sort -n))
	echo "Found ${#VFA_LIST[@]} VFAs: ${VFA_LIST[@]}" >> $LOG_FILE
	VFA_NUMS=($(printf '%s\n' "${VFA_LIST[@]}" | grep -o -E 'flip-[0-9]+' | grep -o -E '[0-9]+'))

	if [ ${#VFA_LIST[@]} -eq 0 ] && [ $T1MAP_PROVIDED -eq 0 ]
		then
		echo "$source_dir No VFAs found! Skipping timepoint..." >> $LOG_FILE
		cd $DATA_DIR
		continue
	fi

	# Without a T1w, a scanner T1 map session uses the DCE reference as its structural image
	if [ ! -f "$source_dir/dce/${PREFIX}_DCE.nii.gz" ] || { [ ! -f "$source_dir/anat/${PREFIX}_T1w.nii.gz" ] && [ $T1MAP_PROVIDED -eq 0 ]; }
	then
		missing_files=""
		[ ! -f "$source_dir/dce/${PREFIX}_DCE.nii.gz" ] && missing_files+=" $source_dir/dce/${PREFIX}_DCE.nii.gz"
		[ ! -f "$source_dir/anat/${PREFIX}_T1w.nii.gz" ] && [ $T1MAP_PROVIDED -eq 0 ] && missing_files+=" $source_dir/anat/${PREFIX}_T1w.nii.gz"

		echo "$source_dir Base file(s) missing! Missing file(s):$missing_files. Skipping timepoint..." >> "$LOG_FILE"
		cd $DATA_DIR
		continue
	fi

	mkdir dce &> /dev/null
	if [ $clean -eq 1 ]
		then
		echo Cleaning folder... $PWD >> $LOG_FILE
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
	export T1MAP_PROVIDED EN_MOTION_CORR EN_BIAS1 EN_BIAS2 EN_Z_NORM USE_AUTO_AIF USE_PYTHON T1_ONLY
	export AIF_SUFFIX AIF_TRAINING_SUFFIX HD_BET_COMMAND AUTO_AIF_PYTHON AUTO_AIF_PATH
	export AUTOAIF_WEIGHT_PATH AUTOAIF_MODEL ROCKETSHIP_PATH GPUFIT_PATH GPUFIT_M_PATH
	export MAX_PARALLEL_JOBS WORKER_STATUS_DIR WORKER_WAIT_TIMEOUT_SECONDS
	session_start=$SECONDS
	session_ran=1
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

	watch_workers
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
		((failures++))
		report_worker_failures
		rm -rf "$WORKER_STATUS_DIR"
		cd "$DATA_DIR" || exit 1
		continue
	fi

	rm -rf "$WORKER_STATUS_DIR"
	cd "$DATA_DIR" || exit 1
	echo "$source_dir preprocessing complete!" >> "$LOG_FILE"
	let successes++
	continue

done

record_session_time
show_progress $count "complete"
[ -t 1 ] && echo

echo Completed preprocessing for $count cases. >> $LOG_FILE
echo $successes subjects succeeded >> $LOG_FILE
echo $failures subjects failed >> $LOG_FILE
echo $((count - successes - failures)) subjects skipped >> $LOG_FILE

if [ $fail -eq 1 ]
	then
	exit 1
fi
