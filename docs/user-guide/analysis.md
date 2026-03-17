# Analysis Pipeline

The analysis phase is driven by `DCE_all.sh`. It takes preprocessed images and produces Ktrans permeability maps, QC plots, and HTML/PDF reports for each case and the full population.

---

## Inputs

These are the outputs of the [preprocessing pipeline](preprocessing.md):

| File |
|---|
| `dce/sub-##_ses-##_desc-bfcz_DCE.nii.gz` |
| `anat/sub-##_ses-##_space-DCEref_T1map.nii` |
| `anat/sub-##_ses-##_space-DCEref_VFA.nii.gz` |
| `dce/sub-##_ses-##_desc-AIF_T1map.nii.gz` |
| `anat/sub-##_ses-##_space-DCEref_desc-brain_mask.nii.gz` |

---

## Main Outputs

| Output File | Description |
|---|---|
| `sub-##_ses-##_Ktrans.nii` | Ktrans permeability map (min⁻¹) |
| `sub-##_ses-##_vp.nii` | Plasma volume fraction map |
| `case_report.html` | Per-case QC report with visualizations |
| `population_report.html` | Population-level summary and outlier detection |

---

## Running Analysis

```bash
./DCE_all.sh -d /path/to/rawdata [options]
```

### Typical invocation

```bash
./DCE_all.sh -d /data/rawdata -s -f -C fullPrep
```

---

## Pipeline Steps

### Step 1 — Ktrans Mapping
**Tool:** ROCKETSHIP (MATLAB)

Runs the extended Tofts pharmacokinetic model on the preprocessed DCE series using the T1 map and AIF mask. Produces voxel-wise Ktrans and vp maps. See [ROCKETSHIP Integration](../integration/rocketship.md) for details.

---

### Step 2 — Gray Matter & CSF Masking
**Tools:** ANTs `antsApplyTransforms`, FSL `fslmaths`

Creates GM and CSF masks from the FAST segmentation, registers them to DCE space, and applies them to exclude non-white-matter voxels from the quantitative analysis. This isolates the WM signal relevant to BBB permeability studies.

---

### Step 3 — QC Analysis
**Scripts:** `ktrans_analysis.py`, `ktrans_report.py`

Computes slice-by-slice statistics (mean, median, standard deviation) for T1 and Ktrans within white matter and gray matter masks. Also counts zero-valued voxels and flags slices that may indicate registration or fitting failures.

`ktrans_report.py` then generates a multi-panel slice visualization of the Ktrans map for inclusion in the case report.

---

### Step 4 — Case Report
**Script:** `case_report.py`

Generates a self-contained `case_report.html` for each subject/session. The report includes:

- Ktrans slice-by-slice visualizations
- Registration QC overlays (VFA-on-DCE, MPRAGE-on-DCE)
- AIF curve and quality metrics
- T1 map statistics
- Motion correction plots (if enabled)
- Pipeline parameter summary

Reports are rendered from Jinja2 templates (`template.html`).

---

### Step 5 — Population Report
**Script:** `population_report.py`

After all cases complete, aggregates results into a single `population_report.html`. Includes:

- Group-level Ktrans and T1 statistics
- Outlier detection and flagging
- Missing data tracking
- Per-subject summary table with links to case reports
- Exportable spreadsheet (`.xlsx`)

Processing runs concurrently across cases using threading with file locking for safe aggregation.

---

## Optional: iNESMA Smoothing (`-S`)

When the `-S` flag is passed, the DCE input is smoothed using iNESMA before Ktrans fitting. iNESMA is a GPU-accelerated non-local means filter (`iNESMA_GPU.py`) that uses CUDA via Numba. It reduces noise while preserving spatial structure better than Gaussian smoothing.

!!! note "GPU required"
    iNESMA requires a CUDA-capable GPU. The Docker image includes CUDA 13 support.

---

## All Options

See the [Analysis CLI Reference](../reference/analysis-cli.md) for the full flag list.
