# AIF Selection

The Arterial Input Function (AIF) describes the contrast agent concentration in blood plasma over time and is required for quantitative Ktrans estimation. DCEPrep supports manual, semi-automatic, and fully automatic AIF selection.

---

## Overview

The AIF is represented as a binary mask identifying voxels within the DCE image that correspond to arterial signal. During kinetic modeling, the mean signal within the AIF mask is used as the input function.

DCEPrep enforces that all AIF voxels fall within the brain mask, preventing contamination from extracranial vessels.

---

## Selection Modes

The `-A` flag controls AIF selection mode in `preprocess_all.sh`:

| Flag | Mode | Description |
|---|---|---|
| *(omitted)* | Manual | Use a pre-existing AIF mask file (must be placed at the expected BIDS path) |
| `-A A` | Automatic | Neural network selects AIF voxels automatically |
| `-A M` | Manual-preferred | Use manual mask if found; fall back to automatic |
| `-A T` | Training | Use manual mask **and** generate training data for the neural network |

---

## Automatic AIF (Neural Network)

DCEPrep's automated AIF detection uses a neural network from the companion [vascular_function](https://github.com/petmri/vascular_function) repository.

### Requirements

- The `vascular_function` repo must be available (cloned or mounted in Docker)
- A pre-trained weights file is required; specify its path with `-w [path]`
- In Docker, the default weights file is located at `/opt/vascular_function/model_weight_huber1.h5`

### How it works

The network is invoked via `main_vif.py` from the vascular_function repository. It takes the 4D DCE time-series as input and produces a continuous probability mask indicating the likelihood that each voxel belongs to an artery. The probability mask is then thresholded to produce a binary AIF mask.

The selected AIF voxels are intersected with the brain mask so that only intracranial arterial voxels are included.

### Outputs

| File | Description |
|---|---|
| `desc-AIF_mask.nii.gz` | Binary AIF mask |
| `desc-AIF_float.nii.gz` | Continuous probability mask (pre-threshold) |
| `desc-AIF_mask.svg` | Visualization of the selected AIF region |
| `desc-AIF_curve.svg` | Plot of the mean AIF signal over time |

### Training mode (`-A T`)

Training mode processes the data using the manual AIF mask but also runs the network to generate prediction outputs. This produces paired manual/automatic data that can be used to retrain or fine-tune the network weights.

---

## AIF Quality Metrics

The quality of the selected AIF is scored by `aif_metric.py` using four weighted metrics combined into an **AIFitness** score (0–100 scale):

| Metric | Weight | Description |
|---|---|---|
| Peak ratio | 30% | Sigmoid-weighted ratio of AIF peak to mean signal — higher peaks indicate better arterial contrast |
| Tail ratio | 30% | Washout quality — how well the signal returns toward baseline after the peak |
| Baseline-to-mean | 30% | Baseline stability — a low pre-contrast baseline relative to the mean indicates good contrast uptake |
| Peak timing | 10% | Whether the peak occurs early in the acquisition, as expected physiologically |

The AIFitness score is displayed in the case report. Cases with AIFitness below **59** are automatically flagged in the population report.

---

## Manual AIF

To provide a manual AIF mask:

1. **Draw the mask** using an image viewer that supports NIfTI editing (e.g., FSLeyes, ITK-SNAP, or 3D Slicer). Select voxels within a major intracranial artery (typically the internal carotid or middle cerebral artery) on the DCE reference volume.
2. **Save** the mask as a binary NIfTI file (voxel values of 0 or 1) in the same space and dimensions as the DCE image.
3. **Place** the file at the expected BIDS path within the derivatives folder:

```
derivatives/dceprep/sub-##/ses-##/dce/sub-##_ses-##_desc-AIF_mask.nii.gz
```

A custom suffix can be specified with the `-a [suffix]` flag if your mask uses a different naming convention (`.nii.gz` is appended automatically).

---

## AIF File Naming

The AIF mask file is expected at:

```
dce/sub-##_ses-##_desc-AIF_mask.nii.gz
```

A custom suffix can be specified with the `-a [suffix]` flag (`.nii.gz` is appended automatically).
