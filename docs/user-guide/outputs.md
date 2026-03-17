# Pipeline Outputs

This page describes the files produced by DCEPrep's preprocessing and analysis phases.

---

## Directory Structure

Outputs are written to a `derivatives/` folder alongside your `rawdata/`, following BIDS derivative conventions:

```
rawdata/
derivatives/
└── sub-01/
    └── ses-01/
        ├── anat/
        ├── dce/
        ├── case_report.html
        └── [comparison_name]/     ← if using -C flag
            ├── anat/
            └── dce/
population_report.html             ← at derivatives root
```

---

## Preprocessing Outputs

### Core outputs

| File | Description |
|---|---|
| `dce/sub-##_ses-##_desc-bfcz_DCE.nii.gz` | Final preprocessed DCE: bias-corrected (`b`), z-normalized (`z`) |
| `anat/sub-##_ses-##_space-DCEref_T1map.nii` | Quantitative T1 map registered to DCE space |
| `anat/sub-##_ses-##_space-DCEref_VFA.nii.gz` | VFA image registered to DCE space |
| `dce/sub-##_ses-##_desc-AIF_T1map.nii.gz` | AIF mask in T1 map space |
| `anat/sub-##_ses-##_space-DCEref_desc-brain_mask.nii.gz` | Brain mask in DCE space |

### Intermediate files

| File | Description |
|---|---|
| `dce/sub-##_ses-##_desc-hmc_DCE.nii` | Head-motion-corrected DCE (before bias/z-norm) |
| `anat/sub-##_ses-##_space-DCEref_T1w.nii.gz` | MPRAGE registered to DCE space |
| `anat/sub-##_ses-##_space-DCEref_T1w.mat` | MPRAGE → DCE affine transform |
| `anat/sub-##_ses-##_label-WM_mask.nii.gz` | White matter segmentation mask |
| `anat/sub-##_ses-##_space-DCEref_label-WM_mask.nii.gz` | WM mask in DCE space |

---

## Analysis Outputs

### Quantitative maps

| File | Description |
|---|---|
| `sub-##_ses-##_Ktrans.nii` | Volume transfer constant Ktrans (min⁻¹); primary BBB permeability measure |
| `sub-##_ses-##_vp.nii` | Plasma volume fraction vp (unitless) |

### Reports

| File | Description |
|---|---|
| `case_report.html` | Per-case QC report (self-contained HTML with embedded images) |
| `population_report.html` | Population-level summary (outliers, group stats, spreadsheet export) |

### QC figures

| File | Description |
|---|---|
| `*_ktrans_analysis.png` | Slice-by-slice Ktrans statistics plots |
| `*_ktrans_report.png` | Multi-panel Ktrans slice visualization |
| `*_motion.png` | Motion parameter plots (if `-m` was used) |

---

## Naming Conventions

DCEPrep follows BIDS-derivative naming conventions:

- `desc-bfcz` — bias field corrected (`bfc`) + z-normalized (`z`)
- `desc-hmc` — head motion corrected
- `space-DCEref` — registered to the DCE reference volume
- `label-WM` — white matter label/mask
- `desc-AIF` — arterial input function mask

---

## Comparison Mode Outputs

When using `-C [name]`, all outputs are written into a named subdirectory:

```
derivatives/sub-01/ses-01/
├── noMC/               ← -C noMC
│   ├── anat/
│   └── dce/
└── fullPrep/           ← -C fullPrep
    ├── anat/
    └── dce/
```

This allows side-by-side comparison of runs with different preprocessing choices. See [Comparison Mode](../how-to/comparison-mode.md).

---

## Spreadsheet Export

The population report generates a `.xlsx` spreadsheet in the derivatives root containing per-subject summary statistics for all Ktrans and T1 metrics. This file is suitable for direct import into statistical analysis software.

### File location

```
derivatives/spreadsheets/dataset_ktrans_YYYY-MM-DD.xlsx
```

### Sheets

| Sheet | Contents |
|---|---|
| **Success** | All cases that completed processing and passed automated QC |
| **Pre-Exclude** | Cases auto-flagged for excessive motion (> 3.8 mm displacement) or low AIFitness (< 59) |
| **Fail** | Cases that failed processing (missing files, wmparc errors, etc.) |
| **Missing** | Cases expected but not found in the derivatives |

Each sheet is indexed by `Subject_ID` (format: `sub-##_ses-##`).

### Columns (Success sheet)

The spreadsheet contains the following column groups:

| Group | Columns |
|---|---|
| **Demographics** | Date, APOE, Sex, Age |
| **Scanner** | Machine, Institution, Coil |
| **Acquisition** | TR, Time_resolution, TE, Flip_angle, n_reps |
| **QC** | Approximate SNR, AIFitness, aif_fitted_r2, manual_aif_status, max_disp |
| **T1** | T1_blood, T1_wm_median, T1_gm_median |
| **Ktrans** | Ktrans_wm_median, Ktrans_gm_median, plus per-region medians (Hippo, PhG, Putamen, Pallidum, Thalamus, Caudate, Amygdala, Entorhinal cortex, Fusiform gyrus cortex/WM, Insula WM, Superior/Inferior temporal cortex, Posterior cingulate cortex, Medial temporal cortex) |
| **Vp** | Per-region Vp medians (same regions as Ktrans) |
| **Volume** | Per-region volumes in mm³ (same regions) |
| **Cortical thickness** | Per-region average and std thickness from FreeSurfer aparc (34 regions, bilateral average) |

The Pre-Exclude and Fail sheets include an additional **Reason** column at the beginning.
