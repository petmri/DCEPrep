#!/bin/bash
shopt -s extglob nullglob

source_dir=${source_dir:?source_dir not set}
PREFIX=${PREFIX:?PREFIX not set}
SCRIPT_PATH=${SCRIPT_PATH:?SCRIPT_PATH not set}
SUBJECT_TP_PATH=${SUBJECT_TP_PATH:?SUBJECT_TP_PATH not set}

source "${PREPROCESS_WORKER_DIR:-$SCRIPT_PATH/scripts/preprocess}/preprocess_worker_common.sh"

REF_SPACE=space-DCEref

build_vfa_lists() {
	local vfa_path
	VFA_LIST=()
	VFA_NUMS=()
	for vfa_path in "$source_dir"/anat/*.nii*; do
		case "$vfa_path" in
			*"${PREFIX}_T1w.nii"|*"${PREFIX}_T1w.nii.gz")
				continue
				;;
		esac
		if [[ "$vfa_path" =~ flip-([0-9]+) ]]; then
			VFA_LIST+=("flip-${BASH_REMATCH[1]}")
			VFA_NUMS+=("${BASH_REMATCH[1]}")
		fi
	done
}

T1w_reg() {
	antsRegistration --verbose 0 --dimensionality 3 --float 0 \
		--collapse-output-transforms 1 --output [ anat/${PREFIX}_${REF_SPACE}_T1w,anat/${PREFIX}_${REF_SPACE}_T1w.nii.gz ] \
		--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
		--transform Rigid[ 0.1 ] --metric MI[ $DCE_REF_VOL,${source_dir}/anat/${PREFIX}_T1w.nii.gz,1,32,Regular,0.25 ] \
		--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
	mv anat/${PREFIX}_${REF_SPACE}_T1w0GenericAffine.mat anat/${PREFIX}_from-T1w_to-DCEref.mat
}

VFA_reg() {
	local vfa=$1
	antsRegistration --verbose 0 --dimensionality 3 --float 0 \
		--collapse-output-transforms 1 --output [ anat/${PREFIX}_flip-${vfa}_${REF_SPACE},anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_VFA.nii.gz ] \
		--interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ] \
		--transform Rigid[ 0.1 ] --metric MI[ $DCE_REF_VOL,$source_dir/anat/${PREFIX}_flip-${vfa}_VFA.nii.gz,1,32,Regular,0.25 ] \
		--convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
	mv anat/${PREFIX}_flip-${vfa}_${REF_SPACE}0GenericAffine.mat anat/${PREFIX}_from-VFA${vfa}_to-DCEref.mat
}

VFA_FAST() {
	local vfa=$1
	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_label-brain_VFA.nii.gz
	mv anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_label-brain_VFA_restore* anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_desc-bfc_VFA.nii.gz
	fslmaths anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_desc-bfc_VFA.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_label-WM_VFA.nii.gz
}

T1_FAST() {
	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -g -o anat/${PREFIX}_label- anat/${PREFIX}_label-brain_T1w.nii.gz
	mv anat/${PREFIX}_label-_bias.nii.gz anat/${PREFIX}_desc-bias_T1w.nii.gz
	mv anat/${PREFIX}_label-_seg_0.nii.gz anat/${PREFIX}_label-CSF_mask.nii.gz
	mv anat/${PREFIX}_label-_seg_1.nii.gz anat/${PREFIX}_label-GM_mask.nii.gz
	mv anat/${PREFIX}_label-_seg_2.nii.gz anat/${PREFIX}_label-WM_mask.nii.gz
	rm anat/${PREFIX}_label-_seg.nii.gz
}

build_vfa_lists
if [ ${#VFA_LIST[@]} -eq 0 ]; then
	mark_worker_failed "vfa_t1" "$source_dir No VFAs found! Skipping timepoint..."
fi

log_worker "$source_dir VFA/T1 worker started."

if [ ! -f "anat/${PREFIX}_label-brain_mask.nii.gz" ] && [ -f "$source_dir/anat/${PREFIX}_T1w.nii.gz" ]; then
	if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
		"$HD_BET_COMMAND" -i "$source_dir/anat/${PREFIX}_T1w.nii.gz" -o "anat/${PREFIX}_label-brain.nii.gz" --save_bet_mask &> /dev/null
	else
		"$HD_BET_COMMAND" -i "$source_dir/anat/${PREFIX}_T1w.nii.gz" -o "anat/${PREFIX}_label-brain.nii.gz" -device cpu --save_bet_mask &> /dev/null
	fi
	if [ ! -f "anat/${PREFIX}_label-brain_bet.nii.gz" ] || [ ! -f "anat/${PREFIX}_label-brain.nii.gz" ]; then
		mark_worker_failed "vfa_t1" "$source_dir HD-BET did not create expected output files. Skipping timepoint..."
	fi
	mv anat/${PREFIX}_label-brain_bet.nii.gz anat/${PREFIX}_label-brain_mask.nii.gz
	mv anat/${PREFIX}_label-brain.nii.gz anat/${PREFIX}_label-brain_T1w.nii.gz
fi

t1_fast_started=0
if [ ! -f "anat/${PREFIX}_label-WM_mask.nii.gz" ]; then
	log_worker "$source_dir [T1 FAST segmentation] started"
	t1_fast_start_seconds=$SECONDS
	start_background_job T1_FAST
	t1_fast_started=1
fi

if [ $EN_MOTION_CORR -eq 1 ]; then
	DCE_REF_VOL=dce/${PREFIX}_desc-hmc_DCEref.nii.gz
else
	DCE_REF_VOL=dce/${PREFIX}_DCEref.nii.gz
fi

wait_for_file "$DCE_REF_VOL" "$WORKER_WAIT_TIMEOUT_SECONDS" "dce.failed"
wait_status=$?
if [ $wait_status -eq 1 ]; then
	mark_worker_failed "vfa_t1" "$source_dir Timed out waiting for $DCE_REF_VOL from DCE worker. Skipping timepoint..."
elif [ $wait_status -eq 2 ]; then
	mark_worker_failed "vfa_t1" "$source_dir DCE worker failed before $DCE_REF_VOL was ready. Skipping timepoint..."
fi

t1w_reg_started=0
t1w_reg_pid=
if [ ! -f "anat/${PREFIX}_from-T1w_to-DCEref.mat" ]; then
	T1w_reg &
	t1w_reg_pid=$!
	t1w_reg_started=1
fi

if [ -n "$t1w_reg_pid" ]; then
	wait "$t1w_reg_pid"
fi

T1w_to_DCEref=anat/${PREFIX}_from-T1w_to-DCEref.mat
structural_to_DCEref=$T1w_to_DCEref
	if [ $t1w_reg_started -eq 1 ] && [ ! -f "$T1w_to_DCEref" ]; then
		mark_worker_failed "vfa_t1" "$source_dir Missing T1w-to-DCE transform after registration. Skipping timepoint..."
	fi

	antsApplyTransforms -i anat/${PREFIX}_label-brain_mask.nii.gz -r "$DCE_REF_VOL" -t "$structural_to_DCEref" -o anat/${PREFIX}_${REF_SPACE}_label-brain_desc-pv_mask.nii.gz &> /dev/null
	fslmaths anat/${PREFIX}_${REF_SPACE}_label-brain_desc-pv_mask.nii.gz -thr 1 -bin anat/${PREFIX}_${REF_SPACE}_label-brain_mask.nii.gz &> /dev/null
	rm anat/${PREFIX}_${REF_SPACE}_label-brain_desc-pv_mask.nii.gz
	mark_worker_ready "vfa_t1.brain_mask"
stage_end

stage_start "VFA registration and T1 FAST completion"
for vfa in "${VFA_NUMS[@]}"; do
	if [ ! -f "anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_VFA.nii.gz" ]; then
		start_background_job VFA_reg "$vfa"
	fi
done
wait

if [ $t1_fast_started -eq 1 ]; then
	log_worker "$source_dir [T1 FAST segmentation] completed in $((SECONDS - t1_fast_start_seconds))s"
	if [ ! -f "anat/${PREFIX}_label-WM_mask.nii.gz" ]; then
		mark_worker_failed "vfa_t1" "$source_dir T1 FAST segmentation did not create a WM mask. Skipping timepoint..."
	fi
fi

	antsApplyTransforms -i anat/${PREFIX}_label-WM_mask.nii.gz -r "$DCE_REF_VOL" -t "$structural_to_DCEref" -o anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz &> /dev/null
	fslmaths anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz -thr 0.9 -bin anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz &> /dev/null

	VFA_DYN_LIST=()
	for vfa_path in anat/${PREFIX}_flip-*_${REF_SPACE}_VFA.nii.gz; do
		if [[ "$vfa_path" =~ (flip-[0-9]+) ]]; then
			VFA_DYN_LIST+=("${BASH_REMATCH[1]}")
		fi
	done

	for vfa in "${VFA_DYN_LIST[@]}"; do
		fslslice anat/${PREFIX}_${vfa}_${REF_SPACE}_VFA.nii.gz anat/${PREFIX}_${vfa}_${REF_SPACE}_VFA
	done

	EMPTY_SLICES=0
	problem_slice=0
	for slice in anat/${PREFIX}_${VFA_DYN_LIST[0]}_${REF_SPACE}_VFA*.nii*; do
		if [ "$(fslstats "$slice" -V | awk '{print $1}')" -lt 100 ]; then
			rm "$slice"
			slice=$(echo "$slice" | grep -o -E '_[0-9]+.nii' | grep -o -E '[0-9]+')
			rm anat/${PREFIX}_flip-*_${REF_SPACE}_VFA_slice_$slice.nii*
			problem_slice=$slice
			EMPTY_SLICES=1
			log_worker "Removing empty slice $slice from all images"
		fi
	done

	if [ $EMPTY_SLICES -eq 1 ]; then
		for registered_img in anat/*${REF_SPACE}*.nii*; do
			if [[ "$registered_img" == *slice* ]]; then
				continue
			fi
			reg_img_no_ext=${registered_img%.nii*}
			reg_img_no_ext=${reg_img_no_ext%_slice_*}
			fslslice "$registered_img" "$reg_img_no_ext"
			rm ${reg_img_no_ext}_slice_$problem_slice.nii*
			fslmerge -z "$registered_img" ${reg_img_no_ext}_slice_*.nii* &> /dev/null
		done
		for img in dce/*.nii*; do
			if [[ "$img" == *slice* ]] || [[ "$img" == *.par ]]; then
				continue
			fi
			img_no_ext=${img%.nii*}
			img_no_ext=${img_no_ext%_slice_*}
			fslslice "$img" "$img_no_ext"
			rm ${img_no_ext}_slice_$problem_slice.nii*
			fslmerge -z "$img" ${img_no_ext}_slice_*.nii* &> /dev/null
		done
		for vfa in "${VFA_DYN_LIST[@]}"; do
			fslmerge -z anat/${PREFIX}_${vfa}_${REF_SPACE}_VFA.nii.gz anat/${PREFIX}_${vfa}_${REF_SPACE}_VFA_slice_*.nii* &> /dev/null
		done
		rm anat/*slice_*.nii* dce/*slice_*.nii*
	else
		rm anat/*slice_*.nii*
	fi

	for vfa in "${VFA_DYN_LIST[@]}"; do
		cp anat/${PREFIX}_${vfa}_${REF_SPACE}_VFA.nii.gz anat/${PREFIX}_${vfa}_${REF_SPACE}_label-brain_VFA.nii.gz
	done

	if [ $EN_BIAS1 -eq 1 ]; then
		for vfa in "${VFA_NUMS[@]}"; do
			if [ ! -f "anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_desc-bfc_VFA.nii.gz" ]; then
				start_background_job VFA_FAST "$vfa"
			fi
		done
		wait
		for vfa in "${VFA_NUMS[@]}"; do
			if [ ! -f "anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_desc-bfc_VFA.nii.gz" ]; then
				mark_worker_failed "vfa_t1" "$source_dir Missing bias-corrected VFA flip-${vfa}. Skipping timepoint..."
			fi
			fslmaths anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_desc-bfc_VFA.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz anat/${PREFIX}_flip-${vfa}_${REF_SPACE}_label-WM_VFA.nii.gz
		done
		rm -f "$source_dir"/[0-9]*_masked_[mps]*
	else
		for vfa in "${VFA_DYN_LIST[@]}"; do
			fslmaths anat/${PREFIX}_${vfa}_${REF_SPACE}_label-brain_VFA.nii.gz -mas anat/${PREFIX}_${REF_SPACE}_label-WM_mask.nii.gz anat/${PREFIX}_${vfa}_${REF_SPACE}_label-WM_VFA.nii.gz &> /dev/null
		done
	fi
	mark_worker_ready "vfa_t1.wm_vfa"

	if [ $EN_Z_NORM -eq 1 ]; then
		if [ ! -f "anat/${PREFIX}_${VFA_LIST[0]}_${REF_SPACE}_desc-bfcz_VFA.nii.gz" ]; then
			python3 "$SCRIPT_PATH/scripts/VFA_norm.py" "$SUBJECT_TP_PATH/anat" "$PREFIX" "$EN_BIAS1" &> /dev/null
		fi
		if [ ! -f "anat/${PREFIX}_${VFA_LIST[0]}_${REF_SPACE}_desc-bfcz_VFA.nii.gz" ]; then
			mark_worker_failed "vfa_t1" "$source_dir Missing Z-normalized VFA files. Z-norm likely failed due to non-existent inputs."
		fi
	fi

	VFA_INPUT=""
	if [ $EN_BIAS2 -eq 1 ]; then
		for vfa in "${VFA_NUMS[@]}"; do
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o ${vfa}_BFC_Z.nii ${vfa}_BFC_Z.nii &> /dev/null
			mv ${vfa}_BFC_Z_restore* ${vfa}_bfc2.nii.gz
			rm -f ${vfa}_BFC_Z_[mps]* &> /dev/null
		done
		fslmerge -t VFA.nii.gz "${VFA_NUMS[@]/%/_bfc2.nii.gz}" &> /dev/null
		rm [0-9]*_BFC_Z_*
	elif [ $EN_Z_NORM -eq 1 ]; then
		for vfa in "${VFA_DYN_LIST[@]}"; do
			VFA_INPUT+="anat/${PREFIX}_${vfa}_${REF_SPACE}_desc-bfcz_VFA.nii.gz "
		done
		fslmerge -t anat/${PREFIX}_${REF_SPACE}_desc-bfczunified_VFA.nii.gz $VFA_INPUT
		VFA_INPUT="desc-bfczunified_VFA"
	elif [ $EN_BIAS1 -eq 1 ]; then
		for vfa in "${VFA_DYN_LIST[@]}"; do
			VFA_INPUT+="anat/${PREFIX}_${vfa}_${REF_SPACE}_desc-bfc_VFA.nii.gz "
		done
		fslmerge -t anat/${PREFIX}_${REF_SPACE}_desc-bfcunified_VFA.nii.gz $VFA_INPUT &> /dev/null
		VFA_INPUT="desc-bfcunified_VFA"
	else
		for vfa in "${VFA_DYN_LIST[@]}"; do
			VFA_INPUT+="anat/${PREFIX}_${vfa}_${REF_SPACE}_label-brain_VFA.nii.gz "
		done
		fslmerge -t anat/${PREFIX}_${REF_SPACE}_desc-unified_VFA.nii.gz $VFA_INPUT
		VFA_INPUT="desc-unified_VFA"
	fi
	gunzip -f "anat/${PREFIX}_${REF_SPACE}_$VFA_INPUT.nii.gz"

	if [ ! -f "anat/${PREFIX}_${REF_SPACE}_$VFA_INPUT.nii" ]; then
		mark_worker_failed "vfa_t1" "$source_dir missing VFA file. Component files may have failed."
	fi

	if [ $USE_PYTHON -eq 1 ]; then
		${ROCKETSHIP_PATH}/.venv/bin/python ${ROCKETSHIP_PATH}/run_parametric_python_case.py --subject-source "$source_dir" --subject-tp "$SUBJECT_TP_PATH" --output-dir "$SUBJECT_TP_PATH" --events off
	else
		matlab -nodisplay -r "cd('$ROCKETSHIP_PATH/parametric_scripts/custom_scripts'); addpath '$ROCKETSHIP_PATH'; addpath '$ROCKETSHIP_PATH/dce'; addpath '$ROCKETSHIP_PATH/external_programs'; addpath '$ROCKETSHIP_PATH/external_programs/niftitools'; addpath '$ROCKETSHIP_PATH/parametric_scripts'; addpath '$GPUFIT_PATH'; addpath '$GPUFIT_M_PATH'; T1mapping_fit('$source_dir/anat', '$SUBJECT_TP_PATH/anat', '${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii'); exit;"
	fi
	[ -f "anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii" ] && mv anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_T1map.nii
	[ -f "anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.mat" ] && mv anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.mat anat/${PREFIX}_${REF_SPACE}_T1map.mat
	[ -f "anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.txt" ] && mv anat/T1_map_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.txt anat/${PREFIX}_${REF_SPACE}_T1map.txt
	[ -f "anat/Rsquared_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii" ] && mv anat/Rsquared_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_desc-rsquared_T1map.nii
	[ -f "anat/CI_low_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii" ] && mv anat/CI_low_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_desc-CIlow_T1map.nii
	[ -f "anat/CI_high_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii" ] && mv anat/CI_high_t1_fa_fit_${PREFIX}_${REF_SPACE}_${VFA_INPUT}.nii anat/${PREFIX}_${REF_SPACE}_desc-CIhigh_T1map.nii
	[ -f "anat/${PREFIX}_${REF_SPACE}_T1map.nii" ] && fslmaths anat/${PREFIX}_${REF_SPACE}_T1map.nii -nan anat/${PREFIX}_${REF_SPACE}_T1map_fix.nii &> /dev/null
	mv anat/${PREFIX}_${REF_SPACE}_T1map_fix.nii.gz anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz
	rm anat/${PREFIX}_${REF_SPACE}_T1map.nii
	if [ ! -f anat/${PREFIX}_${REF_SPACE}_T1map.nii.gz ] && [ ! -f anat/${PREFIX}_${REF_SPACE}_T1map.nii ]; then
		mark_worker_failed "vfa_t1" "$source_dir Missing T1 map file. T1 mapping may have failed."
	fi
	mark_worker_ready "vfa_t1.t1map"

	log_worker "$source_dir VFA/T1 worker complete."
	mark_worker_done "vfa_t1"