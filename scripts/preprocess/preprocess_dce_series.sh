#!/bin/bash
shopt -s extglob nullglob

source_dir=${source_dir:?source_dir not set}
PREFIX=${PREFIX:?PREFIX not set}
SCRIPT_PATH=${SCRIPT_PATH:?SCRIPT_PATH not set}
SUBJECT_TP_PATH=${SUBJECT_TP_PATH:?SUBJECT_TP_PATH not set}

source "${PREPROCESS_WORKER_DIR:-$SCRIPT_PATH/scripts/preprocess}/preprocess_worker_common.sh"

REF_SPACE=space-DCEref

should_run_auto_aif() {
	if [ $USE_AUTO_AIF -eq 1 ] || [ ! -f "dce/${PREFIX}_${AIF_SUFFIX}.nii.gz" ] && [ ! -f "dce/${PREFIX}_${AIF_SUFFIX}.nii" ] && [ ! -f "dce/${PREFIX}_${AIF_TRAINING_SUFFIX}.nii.gz" ]; then
		return 0
	fi

	return 1
}

run_auto_aif_inference() {
	local auto_aif_input

	if [ $EN_MOTION_CORR -eq 1 ]; then
		auto_aif_input=dce/${PREFIX}_desc-hmc_DCE.nii.gz
	else
		auto_aif_input=$source_dir/dce/${PREFIX}_DCE.nii.gz
	fi

	"$AUTO_AIF_PYTHON" $AUTO_AIF_PATH/main_vif.py --mode inference --input_path "$auto_aif_input" --save_output_path $PWD/dce \
		--model_weight_path $AUTOAIF_WEIGHT_PATH \
		--model_name $AUTOAIF_MODEL \
		--save_image 1 &> dce/${PREFIX}_desc-autoaif.log
}

DCE_FAST() {
	local index=$1
	local rep_interval=$2
	if [ ! "$index" -eq 0 ]; then
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o rep_$((rep_interval*index-1)).nii
	else
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o rep_0.nii
	fi
}

log_worker "$source_dir DCE worker started."
mkdir -p figures &> /dev/null

if [ $EN_MOTION_CORR -eq 1 ]; then
	if [ ! -f "dce/${PREFIX}_desc-hmc_DCE.nii.gz" ]; then
		mcflirt -in "$source_dir/dce/${PREFIX}_DCE.nii.gz" -refvol 1 -cost mutualinfo -report -plots -o dce/${PREFIX}_desc-hmc_DCE.nii &> /dev/null
	fi
	if [ ! -f "dce/${PREFIX}_desc-hmc_DCE.nii.gz" ]; then
		mark_worker_failed "dce" "$SUBJECT_TP_PATH/dce Missing motion corrected DCE file."
	fi
	max=$(python3 "$SCRIPT_PATH/scripts/max_disp.py" "$SUBJECT_TP_PATH/dce" "${PREFIX}")
	echo -e "$max" > dce/${PREFIX}_desc-hmc_maxdisp.txt
	fslmerge -n 1 dce/${PREFIX}_desc-hmc_DCEref.nii dce/${PREFIX}_desc-hmc_DCE.nii.gz &> /dev/null
else
	dce_input="$source_dir/dce/${PREFIX}_DCE.nii.gz"
	[ -f "$source_dir/dce/${PREFIX}_DCE.nii" ] && dce_input="$source_dir/dce/${PREFIX}_DCE.nii"
	fslmerge -n 1 dce/${PREFIX}_DCEref.nii "$dce_input" &> /dev/null
fi

auto_aif_started=0
auto_aif_pid=
if should_run_auto_aif; then
	start_background_job run_auto_aif_inference
	auto_aif_pid=$!
	auto_aif_started=1
fi

wait_for_file "$WORKER_STATUS_DIR/vfa_t1.brain_mask.ready" "$WORKER_WAIT_TIMEOUT_SECONDS" "vfa_t1.failed"
wait_status=$?
if [ $wait_status -eq 1 ]; then
	mark_worker_failed "dce" "$source_dir Timed out waiting for a DCE-space brain mask. Skipping timepoint..."
elif [ $wait_status -eq 2 ]; then
	mark_worker_failed "dce" "$source_dir VFA/T1 worker failed before the DCE-space brain mask was ready. Skipping timepoint..."
fi

if [ $auto_aif_started -eq 1 ]; then
	wait "$auto_aif_pid"
fi

AIF_MASK_INPUT=""
if should_run_auto_aif; then
	if [ $auto_aif_started -eq 0 ]; then
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

fslmaths anat/${PREFIX}_${REF_SPACE}_label-brain_mask.nii.gz -add "$AIF_MASK_INPUT" -thr 1 -bin anat/${PREFIX}_${REF_SPACE}_label-brainAIF_mask.nii.gz &> /dev/null

if [ $EN_MOTION_CORR -eq 1 ]; then
	fslmaths dce/${PREFIX}_desc-hmc_DCE.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_label-brainAIF_mask.nii.gz dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
else
	fslmaths "$source_dir/dce/${PREFIX}_DCE.nii.gz" -mas anat/${PREFIX}_${REF_SPACE}_label-brainAIF_mask.nii.gz dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
fi

if [ $EN_BIAS1 -eq 1 ]; then
	if [ ! -f "dce/${PREFIX}_desc-bfc_DCE.nii.gz" ]; then
		reps=$(fslnvols dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz)
		rep_interval=$((reps / 8))
		rep_interval=$(echo "scale=0; ($rep_interval + 0.5) / 1" | bc -l)
		fslmerge -n 0 rep_0.nii dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
		for i in {1..8}; do
			fslmerge -n $((rep_interval*i-1)) rep_$((rep_interval*i-1)).nii dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz &> /dev/null
		done
		start_background_job DCE_FAST "0" "$rep_interval"
		for i in {1..8}; do
			start_background_job DCE_FAST "$i" "$rep_interval"
		done
		wait
		fslmerge -t dce/dyn_bias.nii.gz rep_*_bias.nii.gz &> /dev/null
		fslmaths dce/dyn_bias.nii.gz -Tmean dce/mean_dyn_bias_map.nii.gz &> /dev/null
		fslmaths dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz -div dce/mean_dyn_bias_map.nii.gz dce/${PREFIX}_desc-bfc_DCE.nii.gz &> /dev/null
		mv dce/dyn_bias.nii.gz dce/${PREFIX}_desc-biases_DCE.nii.gz
		mv dce/mean_dyn_bias_map.nii.gz dce/${PREFIX}_desc-meanbias_DCE.nii.gz
		rm rep_*.nii.gz
	fi
else
	cp dce/${PREFIX}_desc-AIFincluded_DCE.nii.gz dce/${PREFIX}_desc-bfc_DCE.nii.gz
fi

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

if [ $EN_BIAS1 -eq 1 ]; then
	vfa_dyn_paths=()
	for vfa_dyn_path in anat/${PREFIX}_flip-*_${REF_SPACE}_label-WM_VFA.nii.gz; do
		vfa_dyn_paths+=("$vfa_dyn_path")
	done
	last_vfa_index=$((${#vfa_dyn_paths[@]} - 1))
	if [ $last_vfa_index -lt 0 ]; then
		mark_worker_failed "dce" "$source_dir Missing WM-masked VFA outputs for DCE masking. Skipping timepoint..."
	fi
	fslmaths dce/${PREFIX}_desc-bfc_DCE.nii.gz -mas "${vfa_dyn_paths[$last_vfa_index]}" dce/${PREFIX}_label-WM_DCE.nii.gz &> /dev/null
else
	fslmaths "$source_dir/dce/${PREFIX}_DCE.nii.gz" -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz dce/${PREFIX}_label-WM_DCE.nii.gz &> /dev/null
fi

if [ $EN_Z_NORM -eq 1 ]; then
	python3 "$SCRIPT_PATH/scripts/DCE_norm.py" "$SUBJECT_TP_PATH/dce" &> /dev/null
else
	cp dce/${PREFIX}_desc-bfc_DCE.nii.gz dce/${PREFIX}_desc-bfcz_DCE.nii.gz
fi
gzip -f dce/${PREFIX}_desc-bfcz_DCE.nii

if [ ! -f "dce/${PREFIX}_desc-bfcz_DCE.nii.gz" ]; then
	mark_worker_failed "dce" "$source_dir Missing normalized DCE file."
fi

log_worker "$source_dir DCE worker complete."
mark_worker_done "dce"