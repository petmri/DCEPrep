#!/bin/bash
shopt -s extglob nullglob

source_dir=${source_dir:?source_dir not set}
PREFIX=${PREFIX:?PREFIX not set}
SCRIPT_PATH=${SCRIPT_PATH:?SCRIPT_PATH not set}
SUBJECT_TP_PATH=${SUBJECT_TP_PATH:?SUBJECT_TP_PATH not set}

source "${PREPROCESS_WORKER_DIR:-$SCRIPT_PATH/scripts/preprocess}/preprocess_worker_common.sh"
init_worker_log "dce"

REF_SPACE=space-DCEref

# The large 4D intermediates are written uncompressed to local scratch: gzip, not the
# network share, is what made each fslmaths/fslmerge pass over the DCE series slow.
# Files the pipeline keeps are gzipped into dce/ in the background (publish_async) and
# the worker waits for them (publish_wait) before finishing. Set DCEPREP_SCRATCH to
# choose the scratch location.
DCE_SCRATCH=$(mktemp -d "${DCEPREP_SCRATCH:-${TMPDIR:-/tmp}}/dceprep_${PREFIX}_XXXXXX") \
	|| mark_worker_failed "dce" "$source_dir Could not create a scratch directory. Skipping timepoint..."
PUBLISH_COUNT=0
PUBLISH_PIDS=()

cleanup_dce_scratch() {
	local pid
	for pid in "${PUBLISH_PIDS[@]}"; do
		kill "$pid" 2> /dev/null
	done
	rm -f dce/.*.partial
	rm -rf "$DCE_SCRATCH"
}
trap cleanup_dce_scratch EXIT
trap 'exit 143' TERM INT

# Run an FSL command with uncompressed NIfTI output
fsl_raw() {
	FSLOUTPUTTYPE=NIFTI "$@"
}

# Gzip scratch file $1 to $2 in the background, multithreaded (single-threaded gzip took
# 4 s for a 367 MB series, pgzip.py 0.6 s). The partial file is hidden and has no
# .nii suffix, so the VFA worker's dce/*.nii* slice cleanup never sees it. The job is
# disowned so it does not count against MAX_PARALLEL_JOBS or block a bare wait.
publish_async() {
	local src=$1 dest=$2 n=$PUBLISH_COUNT
	local partial
	partial="$(dirname "$dest")/.$(basename "$dest").partial"
	PUBLISH_COUNT=$((PUBLISH_COUNT + 1))
	(
		if python3 "$SCRIPT_PATH/scripts/pgzip.py" "$src" "$partial" && mv -f "$partial" "$dest"; then
			echo 0
		else
			rm -f "$partial"
			echo 1
		fi > "$DCE_SCRATCH/.publish_$n"
	) &
	PUBLISH_PIDS+=($!)
	disown $!
}

publish_wait() {
	local n
	for ((n = 0; n < PUBLISH_COUNT; n++)); do
		while [ ! -s "$DCE_SCRATCH/.publish_$n" ]; do
			sleep 0.2
		done
		if [ "$(cat "$DCE_SCRATCH/.publish_$n")" != 0 ]; then
			mark_worker_failed "dce" "$source_dir Failed to write a DCE output into $SUBJECT_TP_PATH/dce. Skipping timepoint..."
		fi
	done
	PUBLISH_PIDS=()
}

should_run_auto_aif() {
	if [ $USE_AUTO_AIF -eq 1 ] || [ ! -f "dce/${PREFIX}_${AIF_SUFFIX}.nii.gz" ] && [ ! -f "dce/${PREFIX}_${AIF_SUFFIX}.nii" ] && [ ! -f "dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz" ]; then
		return 0
	fi

	return 1
}

run_auto_aif_inference() {
	local auto_aif_input

	if [ $EN_MOTION_CORR -eq 1 ]; then
		auto_aif_input=$DCE_HMC
	else
		auto_aif_input=$source_dir/dce/${PREFIX}_DCE.nii.gz
	fi

	"$AUTO_AIF_PYTHON" $AUTO_AIF_PATH/main_vif.py --mode inference --input_path "$auto_aif_input" --save_output_path $PWD/dce \
		--model_weight_path $AUTOAIF_WEIGHT_PATH \
		--model_name $AUTOAIF_MODEL \
		--save_image 1 &> dce/${PREFIX}_desc-autoaif.log
}

# FAST on one extracted repetition in scratch; writes rep_<rep>_bias.nii there
DCE_FAST() {
	local rep=$1
	export FSLOUTPUTTYPE=NIFTI
	run_fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o "$DCE_SCRATCH/rep_${rep}.nii"
}

log_worker "$source_dir DCE worker started."
mkdir -p figures

HMC_NAME=${PREFIX}_desc-hmc_DCE
# The DCE reference is volume 1, the volume mcflirt registers the series to, so it is the
# same in the raw and motion-corrected series (checked after mcflirt). Taking it from the
# raw series lets the VFA worker start its registrations without waiting for mcflirt.
dce_input="$source_dir/dce/${PREFIX}_DCE.nii.gz"
if [ $EN_MOTION_CORR -eq 1 ]; then
	DCE_REF_VOL=dce/${PREFIX}_desc-hmc_DCEref.nii.gz
	# A resumed run reuses its motion-corrected series, which may have been trimmed
	[ -f "dce/${HMC_NAME}.nii.gz" ] && dce_input=dce/${HMC_NAME}.nii.gz
else
	DCE_REF_VOL=dce/${PREFIX}_DCEref.nii.gz
	[ -f "$source_dir/dce/${PREFIX}_DCE.nii" ] && dce_input="$source_dir/dce/${PREFIX}_DCE.nii"
fi
# Written under a hidden name and renamed, so the VFA worker never reads a partial file
FSLOUTPUTTYPE=NIFTI_GZ fslmerge -n 1 "dce/.${PREFIX}_DCEref_partial" "$dce_input"
mv "dce/.${PREFIX}_DCEref_partial.nii.gz" "$DCE_REF_VOL"

hmc_made=0
if [ $EN_MOTION_CORR -eq 1 ]; then
	if [ ! -f "dce/${HMC_NAME}.nii.gz" ]; then
		set_worker_step "dce" "DCE motion correction"
		fsl_raw mcflirt -in "$source_dir/dce/${PREFIX}_DCE.nii.gz" -refvol 1 -cost mutualinfo -report -plots -o "$DCE_SCRATCH/${HMC_NAME}.nii"
		if [ ! -f "$DCE_SCRATCH/${HMC_NAME}.nii" ] || [ ! -f "$DCE_SCRATCH/${HMC_NAME}.nii.par" ]; then
			mark_worker_failed "dce" "$SUBJECT_TP_PATH/dce Missing motion corrected DCE file."
		fi
		cp "$DCE_SCRATCH/${HMC_NAME}.nii.par" dce/
		DCE_HMC=$DCE_SCRATCH/${HMC_NAME}.nii
		hmc_made=1
	else
		DCE_HMC=dce/${HMC_NAME}.nii.gz
	fi
fi

# AutoAIF only needs the motion-corrected series, so it can start before that is
# written to the share
auto_aif_started=0
auto_aif_pid=
if should_run_auto_aif; then
	start_background_job run_auto_aif_inference
	auto_aif_pid=$!
	auto_aif_started=1
fi

if [ $EN_MOTION_CORR -eq 1 ]; then
	max=$(python3 "$SCRIPT_PATH/scripts/max_disp.py" "$SUBJECT_TP_PATH/dce" "${PREFIX}")
	echo -e "$max" > dce/${PREFIX}_desc-hmc_maxdisp.txt
	if [ $hmc_made -eq 1 ]; then
		fsl_raw fslmerge -n 1 "$DCE_SCRATCH/hmc_ref.nii" "$DCE_HMC"
		fsl_raw fslmaths "$DCE_SCRATCH/hmc_ref.nii" -sub "$DCE_REF_VOL" -abs "$DCE_SCRATCH/ref_diff.nii"
		if [ "$(fslstats "$DCE_SCRATCH/ref_diff.nii" -R | awk '{print ($2 == 0)}')" != 1 ]; then
			mark_worker_failed "dce" "$source_dir Motion correction changed the reference volume, so $DCE_REF_VOL does not match the motion-corrected series. Skipping timepoint..."
		fi
		publish_async "$DCE_HMC" "dce/${HMC_NAME}.nii.gz"
		publish_wait
	fi
fi
# The VFA worker's empty-slice cleanup trims every dce/*.nii*, so it waits for this
mark_worker_ready "dce.hmc"

set_worker_step "dce" "AutoAIF / waiting for brain mask"
wait_for_file "$WORKER_STATUS_DIR/vfa_t1.brain_mask.ready" "$WORKER_WAIT_TIMEOUT_SECONDS" "vfa_t1.failed"
wait_status=$?
if [ $wait_status -eq 1 ]; then
	mark_worker_failed "dce" "$source_dir Timed out waiting for a DCE-space brain mask. Skipping timepoint..."
elif [ $wait_status -eq 2 ]; then
	mark_worker_failed "dce" "$source_dir VFA/T1 worker failed before the DCE-space brain mask was ready. Skipping timepoint..."
fi

if [ $auto_aif_started -eq 1 ]; then
	set_worker_step "dce" "AutoAIF"
	wait "$auto_aif_pid"
fi

AIF_MASK_INPUT=""
if should_run_auto_aif; then
	if [ $auto_aif_started -eq 0 ]; then
		set_worker_step "dce" "AutoAIF"
		run_auto_aif_inference
	fi
	if [ $EN_MOTION_CORR -eq 1 ]; then
		if [ ! -f "dce/${PREFIX}_desc-hmc_DCE_float_mask.nii" ] || [ ! -f "dce/${PREFIX}_desc-hmc_DCE_mask.nii" ]; then
			mark_worker_failed "dce" "$source_dir AutoAIF failed. See dce/${PREFIX}_desc-autoaif.log. Skipping timepoint..."
		fi
		mv dce/${PREFIX}_desc-hmc_DCE_float_mask.nii dce/${PREFIX}_label-AIF_desc-float_mask.nii
		mv dce/${PREFIX}_desc-hmc_DCE_mask.nii dce/${PREFIX}_label-AIF_desc-topvoxels_mask.nii
		mv dce/${PREFIX}_desc-hmc_DCE_curve.svg figures/${PREFIX}_label-AIF_desc-resampled_mask.svg
		mv dce/${PREFIX}_desc-hmc_DCE_mask.svg figures/${PREFIX}_label-AIF_mask.svg
		AIF_MASK_INPUT="dce/${PREFIX}_label-AIF_desc-topvoxels_mask.nii"
	else
		if [ ! -f "dce/${PREFIX}_DCE_float_mask.nii" ] || [ ! -f "dce/${PREFIX}_DCE_mask.nii" ]; then
			mark_worker_failed "dce" "$source_dir AutoAIF failed. See dce/${PREFIX}_desc-autoaif.log. Skipping timepoint..."
		fi
		mv dce/${PREFIX}_DCE_float_mask.nii dce/${PREFIX}_label-AIF_desc-float_mask.nii
		mv dce/${PREFIX}_DCE_mask.nii dce/${PREFIX}_label-AIF_desc-topvoxels_mask.nii
		mv dce/${PREFIX}_DCE_curve.svg figures/${PREFIX}_label-AIF_desc-resampled_mask.svg
		mv dce/${PREFIX}_DCE_mask.svg figures/${PREFIX}_label-AIF_mask.svg
		AIF_MASK_INPUT="dce/${PREFIX}_label-AIF_desc-topvoxels_mask.nii"
	fi
elif [ $USE_AUTO_AIF -eq 2 ]; then
	if [ -f "dce/${PREFIX}_${AIF_SUFFIX}.nii.gz" ]; then
		AIF_MASK_INPUT="dce/${PREFIX}_${AIF_SUFFIX}.nii.gz"
	elif [ -f "dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz" ]; then
		AIF_MASK_INPUT="dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz"
	fi
else
	AIF_MASK_INPUT="dce/${PREFIX}_${AIF_SUFFIX}.nii.gz"
fi

if [ ! -f "$AIF_MASK_INPUT" ]; then
	mark_worker_failed "dce" "$source_dir Missing AIF mask for DCE masking. Skipping timepoint..."
fi

fslmaths anat/${PREFIX}_${REF_SPACE}_label-brain_mask.nii.gz -add "$AIF_MASK_INPUT" -thr 1 -bin anat/${PREFIX}_${REF_SPACE}_label-brainAIF_mask.nii.gz

if [ $EN_MOTION_CORR -eq 1 ]; then
	dce_series=$DCE_HMC
	# If the VFA worker's empty-slice cleanup has since trimmed dce/ (it rewrites
	# every dce/*.nii*), use that copy so the series matches the trimmed masks
	if [ "$DCE_HMC" != "dce/${HMC_NAME}.nii.gz" ] && \
		[ "$(fslval "dce/${HMC_NAME}.nii.gz" dim3)" != "$(fslval "$DCE_HMC" dim3)" ]; then
		dce_series=dce/${HMC_NAME}.nii.gz
	fi
else
	dce_series=$source_dir/dce/${PREFIX}_DCE.nii.gz
fi
AIF_INCLUDED=$DCE_SCRATCH/${PREFIX}_desc-AIFincluded_DCE.nii
fsl_raw fslmaths "$dce_series" -mas anat/${PREFIX}_${REF_SPACE}_label-brainAIF_mask.nii.gz "$AIF_INCLUDED"
publish_async "$AIF_INCLUDED" "dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz"

DCE_BFC=$DCE_SCRATCH/${PREFIX}_desc-bfc_DCE.nii
if [ $EN_BIAS1 -eq 1 ]; then
	if [ ! -f "dce/${PREFIX}_desc-bfc_DCE.nii.gz" ]; then
		set_worker_step "dce" "DCE bias correction (FAST)"
		reps=$(fslnvols "$AIF_INCLUDED")
		rep_interval=$((reps / 8))
		rep_interval=$(echo "scale=0; ($rep_interval + 0.5) / 1" | bc -l)
		rep_list=(0)
		for i in {1..8}; do
			rep_list+=($((rep_interval*i-1)))
		done
		fast_pids=()
		for rep in "${rep_list[@]}"; do
			fsl_raw fslmerge -n "$rep" "$DCE_SCRATCH/rep_${rep}.nii" "$AIF_INCLUDED"
			start_background_job DCE_FAST "$rep"
			fast_pids+=($!)
		done
		# Wait for the FAST jobs only, not the background gzips
		for pid in "${fast_pids[@]}"; do
			wait "$pid"
		done
		# Same glob order as before (rep_0, rep_15, ..., rep_7), so the same volume order
		fsl_raw fslmerge -t "$DCE_SCRATCH/dyn_bias.nii" "$DCE_SCRATCH"/rep_*_bias.nii
		fsl_raw fslmaths "$DCE_SCRATCH/dyn_bias.nii" -Tmean "$DCE_SCRATCH/mean_dyn_bias_map.nii"
		fsl_raw fslmaths "$AIF_INCLUDED" -div "$DCE_SCRATCH/mean_dyn_bias_map.nii" "$DCE_BFC"
		publish_async "$DCE_SCRATCH/dyn_bias.nii" "dce/${PREFIX}_desc-biases_DCE.nii.gz"
		publish_async "$DCE_SCRATCH/mean_dyn_bias_map.nii" "dce/${PREFIX}_desc-meanbias_DCE.nii.gz"
		publish_async "$DCE_BFC" "dce/${PREFIX}_desc-bfc_DCE.nii.gz"
	else
		DCE_BFC=dce/${PREFIX}_desc-bfc_DCE.nii.gz
	fi
else
	cp "$AIF_INCLUDED" "$DCE_BFC"
	publish_async "$DCE_BFC" "dce/${PREFIX}_desc-bfc_DCE.nii.gz"
fi

set_worker_step "dce" "waiting for T1 worker"
wait_for_file "$WORKER_STATUS_DIR/vfa_t1.wm_vfa.ready" "$WORKER_WAIT_TIMEOUT_SECONDS" "vfa_t1.failed"
wait_status=$?
if [ $wait_status -eq 1 ]; then
	mark_worker_failed "dce" "$source_dir Timed out waiting for WM-masked VFA outputs. Skipping timepoint..."
elif [ $wait_status -eq 2 ]; then
	mark_worker_failed "dce" "$source_dir VFA/T1 worker failed before WM-masked VFA outputs were ready. Skipping timepoint..."
fi

wait_for_file "$WORKER_STATUS_DIR/vfa_t1.t1map.ready" "$WORKER_WAIT_TIMEOUT_SECONDS" "vfa_t1.failed"
wait_status=$?
if [ $wait_status -eq 1 ]; then
	mark_worker_failed "dce" "$source_dir Timed out waiting for the T1 map. Skipping timepoint..."
elif [ $wait_status -eq 2 ]; then
	mark_worker_failed "dce" "$source_dir VFA/T1 worker failed before the T1 map was ready. Skipping timepoint..."
fi
if [ ! -f "anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz" ]; then
	mark_worker_failed "dce" "$source_dir VFA/T1 worker reported a ready T1 map that is missing. Skipping timepoint..."
fi

fslmaths anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz -mas "$AIF_MASK_INPUT" dce/${PREFIX}_label-AIF_T1map.nii

if [ $EN_BIAS1 -eq 1 ] && [ "${T1MAP_PROVIDED:-0}" -eq 0 ]; then
	vfa_dyn_paths=()
	for vfa_dyn_path in anat/${PREFIX}_flip-*_${REF_SPACE}_label-WM_VFA.nii.gz; do
		vfa_dyn_paths+=("$vfa_dyn_path")
	done
	last_vfa_index=$((${#vfa_dyn_paths[@]} - 1))
	if [ $last_vfa_index -lt 0 ]; then
		mark_worker_failed "dce" "$source_dir Missing WM-masked VFA outputs for DCE masking. Skipping timepoint..."
	fi
	fsl_raw fslmaths "$DCE_BFC" -mas "${vfa_dyn_paths[$last_vfa_index]}" "$DCE_SCRATCH/${PREFIX}_label-WM_DCE.nii"
else
	fsl_raw fslmaths "$source_dir/dce/${PREFIX}_DCE.nii.gz" -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz "$DCE_SCRATCH/${PREFIX}_label-WM_DCE.nii"
fi
publish_async "$DCE_SCRATCH/${PREFIX}_label-WM_DCE.nii" "dce/${PREFIX}_label-WM_DCE.nii.gz"

# DCE_norm.py reads *desc-bfc_DCE.nii[.gz] and *label-WM_DCE.nii[.gz] from the directory
# it is given and writes *desc-bfcz_DCE.nii next to them
DCE_BFCZ=$DCE_SCRATCH/${PREFIX}_desc-bfcz_DCE.nii
if [ $EN_Z_NORM -eq 1 ]; then
	set_worker_step "dce" "DCE Z-normalization"
	[ "$DCE_BFC" = "$DCE_SCRATCH/${PREFIX}_desc-bfc_DCE.nii" ] || ln -s "$PWD/$DCE_BFC" "$DCE_SCRATCH/"
	if ! python3 "$SCRIPT_PATH/scripts/DCE_norm.py" "$DCE_SCRATCH" "$SUBJECT_TP_PATH"; then
		mark_worker_failed "dce" "$source_dir DCE Z-normalization (DCE_norm.py) failed."
	fi
elif [[ "$DCE_BFC" == *.gz ]]; then
	gzip -dc "$DCE_BFC" > "$DCE_BFCZ"
else
	cp "$DCE_BFC" "$DCE_BFCZ"
fi
if [ -f "$DCE_BFCZ" ]; then
	publish_async "$DCE_BFCZ" "dce/${PREFIX}_desc-bfcz_DCE.nii.gz"
fi
publish_wait

if [ ! -f "dce/${PREFIX}_desc-bfcz_DCE.nii.gz" ]; then
	mark_worker_failed "dce" "$source_dir Missing normalized DCE file."
fi

log_worker "$source_dir DCE worker complete."
mark_worker_done "dce"