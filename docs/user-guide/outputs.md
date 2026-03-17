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

!!! warning "Stub"
    The exact columns, sheet names, and missing-data encoding in the spreadsheet output need to be documented here.
