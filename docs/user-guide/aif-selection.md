# AIF Selection

The Arterial Input Function (AIF) describes the contrast agent concentration in blood plasma over time and is required for quantitative Ktrans estimation. DCEPrep supports manual, semi-automatic, and fully automatic AIF selection.

!!! warning "Stub article"
    This article is incomplete. Details on the neural network architecture, weight files, training mode, and manual drawing procedure need to be added.

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
| `-A T` | Training | Use manual mask and generate training data for the neural network |

---

## Automatic AIF (Neural Network)

DCEPrep's automated AIF detection uses a neural network from the companion [vascular_function](https://github.com/petmri/vascular_function) repository.

### Requirements

- The `vascular_function` repo must be available (cloned or mounted in Docker)
- A pre-trained weights file is required; specify its path with `-w [path]`

### How it works

!!! warning "Stub"
    The architecture (CNN, U-Net, etc.), input features, and post-processing steps used by the neural network need to be described here.

---

## AIF Quality Metrics

The quality of the selected AIF is scored using four weighted metrics computed by `aif_metric.py`:

| Metric | Description |
|---|---|
| Peak ratio | Ratio of AIF peak to baseline signal |
| Tail ratio | Ratio of AIF tail (late timepoints) to baseline |
| Peak-to-end | Change from peak to end of acquisition |
| Peak timing | Whether the peak occurs at a physiologically expected timepoint |

These scores are displayed in the case report and can be used to flag poor AIF selections.

---

## Manual AIF

!!! warning "Stub"
    Instructions for manually drawing an AIF mask (tooling, expected file path, naming convention) need to be documented here.

---

## AIF File Naming

The AIF mask file is expected at:

```
dce/sub-##_ses-##_desc-AIF_mask.nii.gz
```

A custom suffix can be specified with the `-a [suffix]` flag (`.nii.gz` is appended automatically).
