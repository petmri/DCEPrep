# FreeSurfer White Matter Parcellation

The `-f` flag in `DCE_all.sh` enables FreeSurfer-based white matter parcellation, which divides the WM mask into anatomical subregions. This allows Ktrans to be analyzed separately in specific WM tracts and lobar regions rather than as a whole-brain average.

---

## Overview

Standard DCEPrep analysis computes Ktrans statistics for the whole WM and GM masks. With `-f` enabled, FreeSurfer's **wmparc** atlas is used to subdivide the brain into anatomically meaningful subregions, providing region-specific Ktrans and Vp statistics in the population report and spreadsheet export.

---

## Requirements

- FreeSurfer must be installed (v6.0.0, Linux-centos6_x86_64-stable-pub-v6.0.0-2beb96c)
- FreeSurfer `license.txt` must be available (mounted in Docker)
- FreeSurfer `recon-all` must have been run for each subject (outputs in `derivatives/freesurfer/`)
- Sufficient disk space (~300 MB per subject for FreeSurfer outputs)

---

## Enabling Parcellation

```bash
./DCE_all.sh -d /data/rawdata -f
```

Parcellation runs as part of the analysis pipeline's masking step.

---

## Parcellation Atlas and Registration

DCEPrep uses FreeSurfer's **wmparc** (white matter parcellation) atlas, which combines cortical parcellation labels from the Desikan-Killiany atlas (`aparc`) with subcortical segmentation from `aseg`.

The registration pipeline:

1. `mri_label2vol` converts `wmparc.mgz` from FreeSurfer conformed space to the subject's native T1w space (`rawavg`)
2. `mri_convert` converts the result to NIfTI format
3. `antsApplyTransforms` applies the T1w → DCE rigid transform (with nearest-neighbor interpolation) to bring the parcellation into DCE space
4. The result is saved as `anat/sub-##_ses-##_space-DCEref_seg-wmparc_dseg.nii.gz`

---

## Output Subregions

The following regions are extracted from the wmparc atlas and reported in the population report and spreadsheet:

### Subcortical structures (from `aseg`)

| Region | FreeSurfer label IDs (L/R) |
|---|---|
| Hippocampus | 17 / 53 |
| Putamen | 12 / 51 |
| Pallidum | 13 / 52 |
| Thalamus | 10 / 49 |
| Caudate | 11 / 50 |
| Amygdala | 18 / 54 |

### White matter regions (from `wmparc`)

| Region | FreeSurfer label IDs (L/R) |
|---|---|
| Parahippocampal WM | 1016 / 2016 |
| Fusiform gyrus WM | 3007 / 4007 |
| Insula WM | 3035 / 4035 |

### Cortical regions (from `aparc`)

| Region | FreeSurfer label IDs (L/R) |
|---|---|
| Entorhinal cortex | 1006 / 2006 |
| Fusiform gyrus cortex | 1007 / 2007 |
| Superior temporal cortex | 1030 / 2030 |
| Inferior temporal cortex | 1009 / 2009 |
| Posterior cingulate cortex | 1023 / 2023 |

### Composite region

| Region | Components |
|---|---|
| Medial temporal cortex | Hippocampus + Parahippocampal WM + Entorhinal cortex |

For each region, the population report includes median Ktrans, median Vp, and volume (mm³). The spreadsheet also includes cortical thickness (average and std) for all Desikan-Killiany parcellation regions.

---

## Run Time

FreeSurfer surface reconstruction is computationally expensive. Expect ~6–8 hours per subject on a standard workstation. The `-s` (skip) flag can be used to avoid re-running parcellation for already-processed cases.

!!! tip
    If you only need whole-brain WM Ktrans statistics, omit `-f` to save time. Parcellation adds significant runtime but provides subregion-level granularity.
