# Preprocessing Pipeline

The preprocessing phase is driven by `preprocess_all.sh`. It takes raw BIDS data and produces motion-corrected, bias-corrected, z-normalized images with a T1 map and AIF mask — ready for kinetic modeling.

---

## Inputs

| File | Pattern |
|---|---|
| VFA images (any number of flip angles) | `sub-##_ses-##_flip-##_VFA.nii.gz` |
| DCE image (4D) | `sub-##_ses-##_DCE.nii.gz` |
| T1-weighted MPRAGE | `sub-##_ses-##_T1w.nii.gz` |

---

## Main Outputs

| Output File | Description |
|---|---|
| `dce/sub-##_ses-##_desc-bfcz_DCE.nii.gz` | Bias-corrected, z-normalized DCE series |
| `anat/sub-##_ses-##_space-DCEref_T1map.nii` | T1 map in DCE reference space |
| `anat/sub-##_ses-##_space-DCEref_VFA.nii.gz` | VFA registered to DCE reference |
| `dce/sub-##_ses-##_desc-AIF_T1map.nii.gz` | AIF mask (T1map space) |
| `anat/sub-##_ses-##_space-DCEref_desc-brain_mask.nii.gz` | Brain mask in DCE reference space |

---

## Running Preprocessing

```bash
./preprocess_all.sh -d /path/to/rawdata [options]
```

### Typical invocation

```bash
./preprocess_all.sh -d /data/rawdata -b -c -Z -A -C fullPrep
```

---

## Pipeline Steps

### Step 1 — Brain Extraction
**Tool:** HD-BET (default weights)

Extracts the brain from the T1w MPRAGE. The VFA images are **not** brain-masked at this stage. The resulting brain mask is propagated to DCE space in Step 11.

---

### Step 2 — DCE Head Motion Correction *(optional, `-m`)*
**Tool:** FSL `mcflirt`

Corrects for head motion across DCE time frames. Uses the 2nd volume as the reference with mutual information as the cost function.

```bash
mcflirt -in dce/${PREFIX}_DCE.nii.gz \
        -refvol 1 \
        -cost mutualinfo \
        -report -plots \
        -o dce/${PREFIX}_desc-hmc_DCE.nii
```

---

### Step 3 — MPRAGE → DCE Registration
**Tool:** ANTs `antsRegistration`

Rigidly registers the T1w MPRAGE to the DCE reference volume (frame 2). Uses mutual information with multi-resolution optimization.

```bash
antsRegistration --verbose 0 --dimensionality 3 --float 0 \
  --collapse-output-transforms 1 \
  --output [ anat/${PREFIX}_${REF_SPACE}_T1w, anat/${PREFIX}_${REF_SPACE}_T1w.nii.gz ] \
  --interpolation Linear \
  --use-histogram-matching 0 \
  --winsorize-image-intensities [ 0.005,0.995 ] \
  --transform Rigid[ 0.1 ] \
  --metric MI[ $DCE_REF_VOL, anat/${PREFIX}_T1w.nii.gz, 1,32,Regular,0.25 ] \
  --convergence [ 1000x500x250x100,1e-6,10 ] \
  --shrink-factors 12x8x4x2 \
  --smoothing-sigmas 4x3x2x1vox
```

---

### Step 4 — VFA → DCE Registration
**Tool:** ANTs `antsRegistration`

Rigidly registers each VFA image to the DCE reference volume, using the same parameters as Step 3. Applied to every flip angle independently.

---

### Step 5 — MPRAGE White Matter Segmentation
**Tool:** FSL `fast`

Segments the brain-extracted MPRAGE into white matter, gray matter, and CSF. The WM mask is used downstream for bias correction quality assessment and (optionally) FreeSurfer parcellation.

```bash
fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve -g \
     -o anat/${PREFIX}_label- \
     anat/${PREFIX}_desc-brain_T1w.nii.gz
```

---

### Step 6 — Apply MPRAGE → DCE Transform to WM Mask
**Tool:** ANTs `antsApplyTransforms`

Warps the WM segmentation mask from MPRAGE space into DCE reference space using the transform computed in Step 3.

---

### Step 7 — VFA Bias Field Correction *(optional, `-b`)*
**Tool:** FSL `fast`

Estimates and removes the low-frequency intensity non-uniformity (bias field) from each registered VFA image.

```bash
fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -B --nopve \
     -o anat/${PREFIX}_${VFA}_${REF_SPACE}_desc-brain_VFA.nii.gz
```

---

### Step 8 — VFA Z-axis Normalization *(optional, `-Z`)*
**Script:** `VFA_norm.py`

Corrects slice-dependent intensity variations along the z-axis in VFA images. Fits a double Gaussian model (or polynomial fallback) to the slice-wise intensity profile and normalizes each slice to remove scanner-related z-axis gradients. Handles empty slices gracefully.

This step is particularly important for multi-site studies where receiver coil profiles vary across scanners.

---

### Step 9 — Second VFA Bias Field Correction *(optional, `-B`)*
**Tool:** FSL `fast`

Applies a second round of bias field correction after z-normalization. Useful when z-normalization changes the field enough to warrant re-correction.

---

### Step 10 — T1 Map Generation
**Tool:** ROCKETSHIP (`run_dce_cli.m`)

Generates a quantitative T1 map from the bias-corrected, z-normalized VFA images using variable flip angle fitting. See [ROCKETSHIP Integration](../integration/rocketship.md).

---

### Step 11 — Apply MPRAGE → DCE Transform to Brain Mask
**Tool:** ANTs `antsApplyTransforms`

Projects the HD-BET brain mask from MPRAGE space into DCE reference space.

---

### Step 12 — AIF Selection
**Script:** Neural network from the [AutoAIF repo](https://github.com/petmri/AutoAIF) *(optional, `-A`)*

Automatically identifies the arterial input function (AIF) voxels within the brain mask. Three modes are available via `-A`:

| Mode | Flag | Behavior |
|---|---|---|
| Fully automatic | `-A A` | Neural network selects AIF |
| Manual if available | `-A M` | Uses existing manual AIF mask if found, otherwise automatic |
| Manual + training | `-A T` | Uses manual mask + generates training data |

The AIF mask is constrained to lie within the brain mask. See [AIF Selection](aif-selection.md) for details.

---

### Step 13 — DCE Bias Field Correction *(optional, `-b`)*
**Tool:** FSL `fast`

Corrects bias in the DCE series by averaging bias fields estimated from the first frame and 8 evenly spaced temporal samples.

```bash
fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -b --nopve \
     -o rep_$((rep_interval*i-1)).nii
```

---

### Step 14 — DCE Z-axis Normalization *(optional, `-Z`)*
**Script:** `DCE_norm.py`

Applies the same double Gaussian z-axis normalization as Step 8, but to the full 4D DCE series. Each temporal frame is normalized independently while preserving temporal dynamics.

---

## All Options

See the [Preprocessing CLI Reference](../reference/preprocessing-cli.md) for the full flag list.
