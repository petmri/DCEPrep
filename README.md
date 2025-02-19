# DCEprep
The `main` branch is stable. Checkout a tag if you want something super stable.
## Requires FSL, ANTS, Matlab, ROCKETSHIP + parametric_scripts, Python, and BIDS compliant data.
Used FSL 6.0, ANTS, freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.0-2beb96c (wm parcellation), Python 3.8.10/3.10

## Installation
### Cloning
In your intended destination directory:
`git clone https://github.com/petmri/DCEprep.git`
### Docker (easy, consistent, ~18 GB)
The easiest way to run the docker is to use a simple script included with this repo: `run_docker.sh`. It will automatically pull the Docker image and run it.

_**MAKE SURE MATLAB & FREESURFER LICENSE FILES, DATA DIRECTORY, SCRIPT PREFERENCE FOLDER (docker/files/), AND /etc/ ARE SHARED WITH DOCKER**_

Make sure also that you change the data directory on line 24 to fit your data set.

`./run_docker.sh`

If you just want to pull the image

`docker pull lsaca05/dce:<MATLAB_release>-<branch>`

Example: `docker pull lsaca05/dce:R2022a-dev`

See [tags](https://hub.docker.com/repository/docker/lsaca05/dce/tags) for release options.

## Pipeline Structure
### `preprocess_all`
Inputs: Any number of flip angles `sub-##_ses-##_flip-##_VFA.nii.gz`, `sub-##_ses-##_DCE.nii.gz`, `sub-##_ses-##_T1w.nii.gz`

Main Outputs: `dce/sub-##_ses-##_desc-bfcz_DCE.nii.gz` `anat/sub-##_ses-##_space-DCEref_T1map.nii` `anat/sub-##_ses-##_space-DCEref_VFA.nii.gz` `dce/sub-##_ses-##_desc-AIF_T1map.nii.gz` `anat/sub-##_ses-##_space-DCEref_desc-brain_mask.nii.gz`

Options: `-d [rawdata_path]: REQUIRED - specify path to your BIDS raw data folder`

`-a: specify AIF suffix (default is 'desc-AIF_mask'). ".nii.gz" will be appended to the suffix.`

`-A: enable AutoAIF with argument A (All automatic), M (Manual if available), or T (Manual + Training if available)` (requires [vascular_function repo and weights](https://github.com/petmri/vascular_function))

`-b: enable first round of bias field correction`

`-B: enable second round of bias field corrections, post-Z-norm if enabled`

`-c: clean case's derivative folder prior to processing, ensures \"fresh\" runs but cannot use skips`

`-C [name]: enable comparison mode, which will output all files to the specified directory within each timepoint. Spits out results for that named run. Useful for comparing, say, no corrections vs corrections`

`-m: enable motion correction`

`-s: skip preprocessing if DCE input file already exists`

`-T [dir_path]: target the subject(s)/session(s) to run (default is 'sub-*/ses-*/')`

`-t: only run up to T1 mapping`

`-w [path]: specify the path to the AutoAIF weights file`

`-Z: enable z-slice normalization`


Example: `./preprocess_all.sh -d /media/network_mriphysics/USC-PPG/bids_test/rawdata -b -c -Z -A -C noMC`
#### Step Summary
1. **Brain Extraction** of T1w MPRAGE using `HD-BET` with default weights (does not brain mask VFAs).
2. 
    <details>
    <summary><b>DCE Motion Correction</b> using FSL <code>mcflirt</code> targeting 2nd frame of DCE with mutualinfo for cost function</summary>
    <code>mcflirt -in $source_dir/dce/${PREFIX}_DCE.nii.gz -refvol '${source_dir}/dce/${PREFIX}_DCE.nii.gz[1]' -cost mutualinfo -report -plots -o dce/${PREFIX}_desc-hmc_DCE.nii
    </code>
    </details>
3. 
    <details>
    <summary><b>MPRAGE->DCE Registration</b> using ANTS <code>antsRegistration</code></summary>
    <code>
    antsRegistration --verbose 0 --dimensionality 3 --float 0
        --collapse-output-transforms 1 --output [ anat/${PREFIX}_${REF_SPACE}_T1w,anat/${PREFIX}_${REF_SPACE}_T1w.nii.gz ]
        --interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ]
        --transform Rigid[ 0.1 ] --metric MI[ $DCE_REF_VOL,${source_dir}/anat/${PREFIX}_T1w.nii.gz,1,32,Regular,0.25 ]
        --convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
    </code>
    </details>
4. 
    <details>
    <summary><b>VFA->DCE Registration</b> using ANTS <code>antsRegistration</code></summary>
    <code>
    antsRegistration --verbose 0 --dimensionality 3 --float 0
        --collapse-output-transforms 1 --output [ anat/${PREFIX}_flip-${VFA}_${REF_SPACE},anat/${PREFIX}_flip-${VFA}_${REF_SPACE}_VFA.nii.gz ]
        --interpolation Linear --use-histogram-matching 0 --winsorize-image-intensities [ 0.005,0.995 ]
        --transform Rigid[ 0.1 ] --metric MI[ $DCE_REF_VOL,$source_dir/anat/${PREFIX}_flip-${VFA}_VFA.nii.gz,1,32,Regular,0.25 ]
        --convergence [ 1000x500x250x100,1e-6,10 ] --shrink-factors 12x8x4x2 --smoothing-sigmas 4x3x2x1vox
    </code>
    </details>
5. 
    <details>
    <summary><b>MPRAGE White Matter Segmentation</b> using FSL <code>fast</code></summary>
    <code>
    fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -g -o anat/${PREFIX}_label- anat/${PREFIX}_desc-brain_T1w.nii.gz
    </code>
    </details>
6. **Apply MPRAGE->DCE to T1 wm mask** using ANTS `antsApplyTransforms`
7. 
    <details>
    <summary><b>VFA Bias Field Correction</b> using FSL <code>fast</code></summary>
    <code>
    fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve -o anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-brain_VFA.nii.gz
    </code>
    </details>
8. **VFA Z-axis Normalization** using double gaussian fitting `VFA_norm.py`
9. **Second VFA Bias Field Correction** using FSL `fast`
10. **Make T1 maps with ROCKETSHIP**
11. **Apply MPRAGE->DCE to T1 brain mask** using ANTS `antsApplyTransforms`
12. **Draw AIF with Neural Network**, ensure AIF is included in brain mask
13. 
    <details>
    <summary><b>DCE Bias Field Correction</b> by taking the first plus 8 evenly spaced t-slice samples and averaging their bias fields generated by FSL  <code>fast</code></summary>
    <code>
    fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -o rep_$((rep_interval*i-1)).nii
    </code>
    </details>
14. **DCE Z-axis Normalization** using double gaussian fitting `DCE_norm.py`

### `DCE_all.sh`
Inputs: `dce/sub-##_ses-##_desc-bfcz_DCE.nii.gz` `anat/sub-##_ses-##_space-DCEref_T1map.nii` `anat/sub-##_ses-##_space-DCEref_VFA.nii.gz` `dce/sub-##_ses-##_desc-AIF_T1map.nii.gz` `anat/sub-##_ses-##_space-DCEref_desc-brain_mask.nii.gz`

Main Outputs: `sub-##_ses-##_Ktrans.nii` `sub-##_ses-##_vp.nii` `case_report.html`, `population_report.html`

Options: `-d: specify raw BIDS data directory (required)`

`-C: enable comparison mode. If a preprocessed -C of the same name does not exist, it will copy essential files from a "standard" run.`

`-f: enable Freesurfer wm parcellation for subregion analysis`

`-s: skip cases already processed`

`-S: enable smoothing of DCE input`

`-T [dir_path]: target the subject(s)/session(s) to run (default is 'sub-*/ses-*/')`

Example: `./DCE_all.sh -d /media/network_mriphysics/USC-PPG/bids_test/rawdata -s -C noMC`
#### Step Summary
1. **Ktrans Mapping with ROCKETSHIP**
2. Create, align, and apply gray matter and CSF masks with antsApplyTransforms and fslmaths
3. Run QC scripts `ktrans_analysis.py` and `ktrans_report.py`
4. Generate a QC report `case_report.html` for the case with `case_report.py`
5. After all cases are finished, generate `population_report.html` using `population_report.py`.
