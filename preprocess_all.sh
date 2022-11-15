#!/bin/bash
shopt -s extglob
# FSL, AFNI, Matlab, ROCKETSHIP + parametric_scripts, ANTS, and Python are required
# Within parametric_scripts should be a custom scripts folder with T1mapping_fit.m
# control variables
VERSION="1.0.0"
EN_Z_NORM=0
EN_BIAS1=0
EN_BIAS2=0
ff=0
fail=0
clean=0
#EN_MOTION_CORR=1

# options
while getopts ":d:bBZFhc" options; do
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
			;;
		F)
			ff=1
			;;
		h)
			echo "This script runs through all subject folders of a specified main data directory, preprocessing every folder ending in '_timepoint'."
			echo "The output is the DCE input, which are the corrected dynamic images, brain mask, T1 maps."
			echo "-b: enable first round of bias field corrections"
			echo "-B: enable second round of bias field corrections, post-Z-norm if enabled"
			echo "-c: clean generated files prior to processing"
			echo "-Z: enable Z-slice normalization"
			echo "-d: specify main data directory containing all subject folders"
			echo "-F: fail fast, any command failures will end the script"
			echo "-h: display this message"
			exit 0
			;;
		Z)
			EN_Z_NORM=1
			;;
	esac
done

if [ -z "$DATA_DIR" ]
	then
		echo "ERROR: Please use '-d [dir_path]' to pass the path to your main data directory to this script."
		exit 1
fi
cd $DATA_DIR
if [[ "$OSTYPE" == "linux-gnu" ]]; then
	ROCKETSHIP_PATH=$(find $HOME -name '*run_dce_auto.m' -printf '%h\n' -quit)
	SCRIPT_PATH=$(find $HOME -name '*auto_analysis.py' -printf '%h\n' -quit)
else
	ROCKETSHIP_PATH=$(find $HOME -type d -name ROCKETSHIP)
	SCRIPT_PATH=$(find $HOME -type d -name in-house_toolbox)
fi

# Run bias correction on VFA data 
# ------------------------------
for dir in */*_timepoint/; do
	date
	echo Preprocessing ${dir}...
	cd $dir
	SUBJECT_TP_PATH=$(pwd)

	if [ ! -f "2.nii" ] || [ ! -f "5.nii" ] || [ ! -f "10.nii" ] || [ ! -f "12.nii" ] || [ ! -f "15.nii" ] || [ ! -f "DCE.nii" ] || [ ! -f "T1.nii" ]
		then
		echo Base file(s) missing! Expected VFAs 2.nii, 5.nii, 10.nii, 12.nii, 15.nii, DCE.nii, and T1.nii (MP-RAGE). Skipping timepoint...
		continue
	fi
	
	if [ $clean -eq 1 ]
		then
		echo Cleaning folder...
        rm !(2.nii|5.nii|10.nii|12.nii|15.nii|DCE.nii|aif.nii|T1.nii|*.json)
    fi
	
	# HD-BET brain extraction & segmentations from MP-RAGE
	hd-bet -i T1.nii
	fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -g -o segmented_t1 T1_bet.nii.gz
	rm segmented_t1_seg.nii.gz
	rm segmented_t1_pve_0.nii.gz
	rm segmented_t1_pve_1.nii.gz
	rm segmented_t1_pve_2.nii.gz
	rm segmented_t1_mixeltype.nii.gz
	rm segmented_t1_pveseg.nii.gz
	
	bash $SCRIPT_PATH/tktregistration.sh 2.nii segmented_t1_seg_2.nii.gz T1_wm_mask.nii.gz
	fslmaths T1_wm_mask.nii.gz -thr 0.4 -bin T1_wm_mask.nii.gz
			
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
			echo Bias field correction with FAST
			# don't forget to remove all unnecessary images 
			fast -t 3 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 2_masked.nii
			rm 2_masked_mixeltype.nii.gz
			rm 2_masked_pve_0.nii.gz
			rm 2_masked_pve_1.nii.gz
			rm 2_masked_pve_2.nii.gz
			rm 2_masked_pveseg.nii.gz
			rm 2_masked_seg.nii.gz
			3dcalc -a 2_masked.nii -b 2_masked_bias.nii.gz -expr a/b -prefix 2_bfc.nii -overwrite
			
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 5_masked.nii
			rm 5_masked_mixeltype.nii.gz
			rm 5_masked_pve_0.nii.gz
			rm 5_masked_pve_1.nii.gz
			rm 5_masked_pve_2.nii.gz
			rm 5_masked_pveseg.nii.gz
			rm 5_masked_seg.nii.gz
			3dcalc -a 5_masked.nii -b 5_masked_bias.nii.gz -expr a/b -prefix 5_bfc.nii -overwrite
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 10_masked.nii
			rm 10_masked_mixeltype.nii.gz
			rm 10_masked_pve_0.nii.gz
			rm 10_masked_pve_1.nii.gz
			rm 10_masked_pve_2.nii.gz
			rm 10_masked_pveseg.nii.gz
			rm 10_masked_seg.nii.gz
			3dcalc -a 10_masked.nii -b 10_masked_bias.nii.gz -expr a/b -prefix 10_bfc.nii -overwrite
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 12_masked.nii
			rm 12_masked_mixeltype.nii.gz
			rm 12_masked_pve_0.nii.gz
			rm 12_masked_pve_1.nii.gz
			rm 12_masked_pve_2.nii.gz
			rm 12_masked_pveseg.nii.gz
			rm 12_masked_seg.nii.gz
			3dcalc -a 12_masked.nii -b 12_masked_bias.nii.gz -expr a/b -prefix 12_bfc.nii -overwrite
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 15_masked.nii
			rm 15_masked_mixeltype.nii.gz
			rm 15_masked_pve_0.nii.gz
			rm 15_masked_pve_1.nii.gz
			rm 15_masked_pve_2.nii.gz
			rm 15_masked_pveseg.nii.gz
			rm 15_masked_seg.nii.gz
			3dcalc -a 15_masked.nii -b 15_masked_bias.nii.gz -expr a/b -prefix 15_bfc.nii -overwrite
		else
			echo Found BFC VFAs. Skipping BFC...
		fi
		# threshold and binarize wm mask
		#fslmaths 15_masked_seg.nii.gz -thr 3 -uthr 3 15_wm.nii
		
		# apply wm mask to all VFAs
		fslmaths 2_bfc.nii -mas T1_wm_mask.nii.gz 2_bfc_wm.nii 
		fslmaths 5_bfc.nii -mas T1_wm_mask.nii.gz 5_bfc_wm.nii
		fslmaths 10_bfc.nii -mas T1_wm_mask.nii.gz 10_bfc_wm.nii
		fslmaths 12_bfc.nii -mas T1_wm_mask.nii.gz 12_bfc_wm.nii
		fslmaths 15_bfc.nii -mas T1_wm_mask.nii.gz 15_bfc_wm.nii
	else
		# dumb file name management for norm only runs
		fslmaths 2.nii -mas T1_bet_mask.nii.gz 2_bfc.nii 
		fslmaths 5.nii -mas T1_bet_mask.nii.gz 5_bfc.nii
		fslmaths 10.nii -mas T1_bet_mask.nii.gz 10_bfc.nii
		fslmaths 12.nii -mas T1_bet_mask.nii.gz 12_bfc.nii
		fslmaths 15.nii -mas T1_bet_mask.nii.gz 15_bfc.nii
		
		echo Skipping BFC... but still segmenting one VFA for matter masks
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 15_bfc.nii
		rm 15_bfc_mixeltype.nii.gz
		rm 15_bfc_pve_0.nii.gz
		rm 15_bfc_pve_1.nii.gz
		rm 15_bfc_pve_2.nii.gz
		rm 15_bfc_pveseg.nii.gz
		#rm 15_bfc_seg.nii.gz
		
		# threshold and binarize wm mask
		#fslmaths 15_bfc_seg.nii.gz -thr 3 -uthr 3 15_wm.nii
		
		# apply wm mask to all VFAs
		fslmaths 2_bfc.nii -mas T1_wm_mask.nii.gz 2_bfc_wm.nii 
		fslmaths 5_bfc.nii -mas T1_wm_mask.nii.gz 5_bfc_wm.nii
		fslmaths 10_bfc.nii -mas T1_wm_mask.nii.gz 10_bfc_wm.nii
		fslmaths 12_bfc.nii -mas T1_wm_mask.nii.gz 12_bfc_wm.nii
		fslmaths 15_bfc.nii -mas T1_wm_mask.nii.gz 15_bfc_wm.nii
		
		# apply MP-RAGE wm mask
		fslmaths 2_bfc.nii -mas T1_wm_mask.nii.gz 2_bfc_wm.nii 
		fslmaths 5_bfc.nii -mas T1_wm_mask.nii.gz 5_bfc_wm.nii
		fslmaths 10_bfc.nii -mas T1_wm_mask.nii.gz 10_bfc_wm.nii
		fslmaths 12_bfc.nii -mas T1_wm_mask.nii.gz 12_bfc_wm.nii
		fslmaths 15_bfc.nii -mas T1_wm_mask.nii.gz 15_bfc_wm.nii
	fi

	# Run Z-axis normalization VFA data
	# ------------------------------
	if [ $EN_Z_NORM -eq 1 ] 
		then
		echo begin slice normalization
		python3 $SCRIPT_PATH/VFA_norm.py $SUBJECT_TP_PATH
	fi

	if [ $ff -eq 1 ]
		then
			if [ ! -f "15_BFC_Z.nii" ]
				then
					echo "Missing Z-normalized files. Z-norm likely failed due to non-existent inputs."
					fail=1
					continue
			fi
	fi

	if [ $EN_BIAS2 -eq 1 ]
		then
		# 2nd Bias correction VFA data
		# ------------------------------
		echo Begin second round of BFC
		# Bias field correction with FAST
		# don't forget to remove all unnecessary images 
		fast -t 3 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 2_BFC_Z.nii
		rm 2_BFC_Z_mixeltype.nii.gz
		rm 2_BFC_Z_pve_0.nii.gz
		rm 2_BFC_Z_pve_1.nii.gz
		rm 2_BFC_Z_pve_2.nii.gz
		rm 2_BFC_Z_pveseg.nii.gz
		rm 2_BFC_Z_seg.nii.gz
		3dcalc -a 2_BFC_Z.nii -b 2_BFC_Z_bias.nii.gz -expr a/b -prefix 2_b2corr.nii -overwrite
		
		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 5_BFC_Z.nii
		rm 5_BFC_Z_mixeltype.nii.gz
		rm 5_BFC_Z_pve_0.nii.gz
		rm 5_BFC_Z_pve_1.nii.gz
		rm 5_BFC_Z_pve_2.nii.gz
		rm 5_BFC_Z_pveseg.nii.gz
		rm 5_BFC_Z_seg.nii.gz
		3dcalc -a 5_BFC_Z.nii -b 5_BFC_Z_bias.nii.gz -expr a/b -prefix 5_b2corr.nii -overwrite

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 10_BFC_Z.nii
		rm 10_BFC_Z_mixeltype.nii.gz
		rm 10_BFC_Z_pve_0.nii.gz
		rm 10_BFC_Z_pve_1.nii.gz
		rm 10_BFC_Z_pve_2.nii.gz
		rm 10_BFC_Z_pveseg.nii.gz
		rm 10_BFC_Z_seg.nii.gz
		3dcalc -a 10_BFC_Z.nii -b 10_BFC_Z_bias.nii.gz -expr a/b -prefix 10_b2corr.nii -overwrite

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 12_BFC_Z.nii
		rm 12_BFC_Z_mixeltype.nii.gz
		rm 12_BFC_Z_pve_0.nii.gz
		rm 12_BFC_Z_pve_1.nii.gz
		rm 12_BFC_Z_pve_2.nii.gz
		rm 12_BFC_Z_pveseg.nii.gz
		rm 12_BFC_Z_seg.nii.gz
		3dcalc -a 12_BFC_Z.nii -b 12_BFC_Z_bias.nii.gz -expr a/b -prefix 12_b2corr.nii -overwrite

		fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 15_BFC_Z.nii
		rm 15_BFC_Z_mixeltype.nii.gz
		rm 15_BFC_Z_pve_0.nii.gz
		rm 15_BFC_Z_pve_1.nii.gz
		rm 15_BFC_Z_pve_2.nii.gz
		rm 15_BFC_Z_pveseg.nii.gz
		rm 15_BFC_Z_seg.nii.gz
		3dcalc -a 15_BFC_Z.nii -b 15_BFC_Z_bias.nii.gz -expr a/b -prefix 15_b2corr.nii -overwrite
		
		# concatenates 5 images in one VFA.nii image  
		3dTcat -prefix VFA.nii 2_b2corr.nii 5_b2corr.nii 10_b2corr.nii 12_b2corr.nii 15_b2corr.nii -overwrite
		
	elif [ $EN_Z_NORM -eq 1 ] 
		then
		echo Concatenating Z-norm\'d images
		# concatenates 5 images in one VFA.nii image
		3dTcat -prefix VFA.nii 2_BFC_Z.nii 5_BFC_Z.nii 10_BFC_Z.nii 12_BFC_Z.nii 15_BFC_Z.nii -overwrite

	elif [ $EN_BIAS1 -eq 1 ]
		then
		echo Concatenating non Z\'d images
		3dTcat -prefix VFA.nii 2_bfc.nii 5_bfc.nii 10_bfc.nii 12_bfc.nii 15_bfc.nii -overwrite
	else
		echo Concatenating raw images
		3dTcat -prefix VFA.nii 2_masked.nii 5_masked.nii 10_masked.nii 12_masked.nii 15_masked.nii -overwrite
	fi
	
	if [ $ff -eq 1 ]
		then
			if [ ! -f "VFA.nii" ]
				then
					echo "Missing VFA file. Component files may have failed."
					fail=1
					continue
			fi
	fi
	
	# motion correction of VFA
	# ------------------------------
	mcflirt -in VFA.nii -refvol 'VFA.nii[0]' -cost mutualinfo -report -verbose -plots -o VFA_mc.nii
	gunzip -f VFA_mc.nii.gz
	
	if [ $ff -eq 1 ]
		then
			if [ ! -f "VFA_mc.nii" ]
				then
					echo "Missing VFA_mc file. Motion correction may have failed."
					fail=1
					continue
			fi
	fi
	# smooth
	#3dBlurToFWHM -input VFA_mc.nii -FWHM 5 -prefix VFA_mc_blurred.nii
	
	# T1 mapping where the input image is 'VFA.motioncorrected.nii'
	# ------------------------------
	matlab -nodisplay -r "cd('$ROCKETSHIP_PATH/parametric_scripts/custom_scripts'); addpath '$ROCKETSHIP_PATH'; addpath '$ROCKETSHIP_PATH/dce'; addpath '$ROCKETSHIP_PATH/external_programs'; addpath '$ROCKETSHIP_PATH/external_programs/niftitools'; addpath '$ROCKETSHIP_PATH/parametric_scripts'; T1mapping_fit('$SUBJECT_TP_PATH/'); exit;"
	if [ $ff -eq 1 ]
		then
			if [ ! -f "T1_map_t1_fa_fit_VFA_mc.nii" ]
				then
					echo "Missing T1 map file. T1 mapping may have failed."
					fail=1
					continue
			fi
	fi
	# Motion correction of dynamic images using AFNI
	# ------------------------------
	echo Motion correcting dynamic images...
	mcflirt -in DCE.nii -refvol 'DCE.nii[1]' -cost mutualinfo -report -plots -o DCE_mc.nii
	max=$(python3 $SCRIPT_PATH/max_disp.py $SUBJECT_TP_PATH)
	echo -e "\e[1;33m$max\e[0m"
	if [ $ff -eq 1 ]
		then
			if [ ! -f "DCE_mc.nii.gz" ]
				then
					echo "Missing motion corrected DCE file."
					fail=1
					continue
			fi
	fi
	# Align T1 map with Dynamic data
	# ------------------------------
	# MC or no?
	3dTcat -prefix ref_rep.nii DCE_mc.nii'[1]' -overwrite
	# FRAUDSURFER doesn't really do anything
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_map_t1_fa_fit_VFA_mc.nii t1_map_fixed_use_me.nii.gz
	antsRegistrationSyN.sh -d 3 -t t -f ref_rep.nii -m T1_map_t1_fa_fit_VFA_mc.nii -o t1_map_fixed_use_me
	mv t1_map_fixed_use_meWarped.nii.gz t1_map_fixed_use_me.nii.gz
	rm t1_map_fixed_use_meInverseWarped.nii.gz
	rm t1_map_fixed_use_me0GenericAffine.mat
	
	if [ $ff -eq 1 ]
		then
			if [ ! -f "t1_map_fixed_use_me.nii.gz" ]
				then
					echo "Missing registered T1 map."
					fail=1
					continue
			fi
	fi
	# align and apply brain mask
	#flirt -in T1.nii -ref ref_rep.nii -dof 12 -omat T1toDCE.mat -o T1_dyn.nii
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1.nii T1_dyn.nii.gz
	antsRegistrationSyN.sh -d 3 -t r -f ref_rep.nii -m T1.nii -o T1_dyn
	mv T1_dynWarped.nii.gz T1_dyn.nii.gz
	
	#flirt -in T1_bet_mask.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_bet_mask_dyn.nii
	#fslmaths T1_bet_mask_dyn.nii -bin T1_bet_mask_dyn.nii
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_bet_mask.nii.gz T1_bet_mask_dyn.nii.gz
	
	antsRegistrationSyN.sh -d 3 -t t -f ref_rep.nii -m T1_bet_mask.nii.gz -o T1_bet_mask_dyn
	mv T1_bet_mask_dynWarped.nii.gz T1_bet_mask_dyn.nii.gz
	rm T1_bet_mask_dynInverseWarped.nii.gz
	rm T1_bet_mask_dyn0GenericAffine.mat
	
	# ensure AIF is included in mask
	fslcpgeom 2.nii T1_bet_mask_dyn.nii.gz
	cp aif.nii aif_aligned.nii
	fslcpgeom T1_bet_mask_dyn.nii.gz aif_aligned.nii
	fslmaths aif_aligned.nii -thr 0 aif_pos.nii
	rm aif_aligned.nii
	fslmaths T1_bet_mask_dyn.nii.gz -add aif_pos.nii -thr 1 -bin T1_bet_mask_dyn_aif.nii
	fslmaths DCE_mc.nii -mas T1_bet_mask_dyn_aif.nii.gz DCE_mc_masked.nii
		
	if [ $EN_BIAS1 -eq 1 ]
		then
		if [ ! -f "DCE_mc_bfc.nii" ]
			then
			# Applying bias field correction on dynamic images
			# ------------------------------
			echo Applying BFC to dynamic images...
			3dTcat -prefix 1st_rep.nii DCE_mc_masked.nii'[0]' -overwrite # extract images from different DCE repetitions
			3dTcat -prefix 5th_rep.nii DCE_mc_masked.nii'[4]' -overwrite
			3dTcat -prefix 10th_rep.nii DCE_mc_masked.nii'[9]' -overwrite
			3dTcat -prefix 20th_rep.nii DCE_mc_masked.nii'[19]' -overwrite
			3dTcat -prefix 30th_rep.nii DCE_mc_masked.nii'[29]' -overwrite
			3dTcat -prefix 40th_rep.nii DCE_mc_masked.nii'[39]' -overwrite
			3dTcat -prefix 50th_rep.nii DCE_mc_masked.nii'[49]' -overwrite
			3dTcat -prefix 60th_rep.nii DCE_mc_masked.nii'[59]' -overwrite
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 1st_rep.nii
			rm 1st_rep_mixeltype.nii.gz
			rm 1st_rep_pve_0.nii.gz
			rm 1st_rep_pve_1.nii.gz
			rm 1st_rep_pve_2.nii.gz
			rm 1st_rep_pveseg.nii.gz
			rm 1st_rep_seg.nii.gz
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 5th_rep.nii
			rm 5th_rep_mixeltype.nii.gz
			rm 5th_rep_pve_0.nii.gz
			rm 5th_rep_pve_1.nii.gz
			rm 5th_rep_pve_2.nii.gz
			rm 5th_rep_pveseg.nii.gz
			rm 5th_rep_seg.nii.gz
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 10th_rep.nii
			rm 10th_rep_mixeltype.nii.gz
			rm 10th_rep_pve_0.nii.gz
			rm 10th_rep_pve_1.nii.gz
			rm 10th_rep_pve_2.nii.gz
			rm 10th_rep_pveseg.nii.gz
			rm 10th_rep_seg.nii.gz
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 20th_rep.nii
			rm 20th_rep_mixeltype.nii.gz
			rm 20th_rep_pve_0.nii.gz
			rm 20th_rep_pve_1.nii.gz
			rm 20th_rep_pve_2.nii.gz
			rm 20th_rep_pveseg.nii.gz
			rm 20th_rep_seg.nii.gz
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 30th_rep.nii
			rm 30th_rep_mixeltype.nii.gz
			rm 30th_rep_pve_0.nii.gz
			rm 30th_rep_pve_1.nii.gz
			rm 30th_rep_pve_2.nii.gz
			rm 30th_rep_pveseg.nii.gz
			rm 30th_rep_seg.nii.gz
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 40th_rep.nii
			rm 40th_rep_mixeltype.nii.gz
			rm 40th_rep_pve_0.nii.gz
			rm 40th_rep_pve_1.nii.gz
			rm 40th_rep_pve_2.nii.gz
			rm 40th_rep_pveseg.nii.gz
			rm 40th_rep_seg.nii.gz
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 50th_rep.nii
			rm 50th_rep_mixeltype.nii.gz
			rm 50th_rep_pve_0.nii.gz
			rm 50th_rep_pve_1.nii.gz
			rm 50th_rep_pve_2.nii.gz
			rm 50th_rep_pveseg.nii.gz
			rm 50th_rep_seg.nii.gz
	
			fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b -o 60th_rep.nii
			rm 60th_rep_mixeltype.nii.gz
			rm 60th_rep_pve_0.nii.gz
			rm 60th_rep_pve_1.nii.gz
			rm 60th_rep_pve_2.nii.gz
			rm 60th_rep_pveseg.nii.gz
			rm 60th_rep_seg.nii.gz
	
			# Concatenation1
			3dTcat -prefix dyn_bias.nii 1st_rep_bias.nii.gz 5th_rep_bias.nii.gz 10th_rep_bias.nii.gz 20th_rep_bias.nii.gz 30th_rep_bias.nii.gz 40th_rep_bias.nii.gz 50th_rep_bias.nii.gz 60th_rep_bias.nii.gz -overwrite
	
			# Computing average across 8 bias field that have been sampled
			3dTstat -mean -prefix mean_dyn_bias_map.nii dyn_bias.nii'[0..7]' -overwrite
	
			# Normalizing motion corrected DCE image with mean bias field 
			3dcalc -a DCE_mc_masked.nii -b mean_dyn_bias_map.nii -expr a/b -prefix DCE_mc_bfc.nii -overwrite
	
			# don't forget to remove all unnecessary images 
			rm 1st_rep.nii
			rm 1st_rep_bias.nii.gz
			rm 5th_rep.nii
			rm 5th_rep_bias.nii.gz
			rm 10th_rep.nii
			rm 10th_rep_bias.nii.gz
			rm 20th_rep.nii
			rm 20th_rep_bias.nii.gz
			rm 30th_rep.nii
			rm 30th_rep_bias.nii.gz
			rm 40th_rep.nii
			rm 40th_rep_bias.nii.gz
			rm 50th_rep.nii
			rm 50th_rep_bias.nii.gz
			rm 60th_rep.nii
			rm 60th_rep_bias.nii.gz
		else
			echo Skipping DCE BFC because it already exists...
		fi
	else
		#echo Motion correcting dynamic set
		#3dvolreg -heptic -verbose -base 'DCE.nii[1]' -dfile DCE_motion.txt -prefix DCE_mc_bfc.nii DCE.nii
		#3dTcat -prefix ref_rep.nii dce_mc_bfc'[1]'
		gunzip -f DCE_mc.nii.gz
		mv DCE_mc.nii DCE_mc_bfc.nii
	fi
	
	# align existing white matter mask to dynamic images and re-binarize
	#flirt -in T1_wm_mask.nii.gz -ref ref_rep.nii -init T1toDCE.mat -applyxfm -o T1_wm_mask_dyn.nii
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_wm_mask.nii.gz T1_wm_mask_dyn.nii.gz
	antsRegistrationSyN.sh -d 3 -t r -f ref_rep.nii -m T1_wm_mask.nii.gz -o T1_wm_mask_dyn
	mv T1_wm_mask_dynWarped.nii.gz T1_wm_mask_dyn.nii.gz
	fslmaths T1_wm_mask_dyn.nii.gz -thr 0.3 -bin T1_wm_mask_dyn.nii.gz
	
	#fslmaths T1_wm_mask_dynWarped.nii -thr 0.7 -bin T1_wm_mask_dyn.nii
	#bash $SCRIPT_PATH/tktregistration.sh ref_rep.nii T1_bet_mask.nii.gz T1_bet_mask_dyn.nii.gz
	#fslmaths 15_wm_mask_dyn.nii.gz -thr 1.7 -bin 15_wm_mask_dyn.nii
	rm T1_wm_mask_dynInverseWarped.nii.gz
	rm T1_wm_mask_dyn0GenericAffine.mat
	
	# apply wm mask to all DCE images
	fslmaths DCE_mc_bfc.nii -mas T1_wm_mask_dyn.nii.gz DCE_mc_bfc_wm.nii.gz

	# normalize dynamic images
	# ------------------------------
	echo Normalizing dynamic images...
	python3 $SCRIPT_PATH/DCE_norm.py $SUBJECT_TP_PATH
	if [ $ff -eq 1 ]
		then
			if [ ! -f "DCE_mc_bfc_norm.nii" ]
				then
					echo "Missing normalized DCE file."
					fail=1
					continue
			fi
	fi
	# smooth dynamic set
	#3dBlurToFWHM -input DCE_mc_bfc_norm.nii -FWHM 4 -prefix DCE_mc_bfc_norm_blurred.nii

	cd ../../
	echo $dir preprocessing complete!
done

if [ $fail -eq 1 ]
	then
	exit 1
fi
