# Pipeline Steps Reference

Quick-reference summary of all steps in both pipeline phases.

---

## Preprocessing (`preprocess_all.sh`)

| Step | Name | Tool | Flag Required |
|---|---|---|---|
| 1 | Brain extraction | HD-BET | — (always runs) |
| 2 | DCE head motion correction | FSL `mcflirt` | `-m` |
| 3 | MPRAGE → DCE registration | ANTs `antsRegistration` | — (always runs) |
| 4 | VFA → DCE registration | ANTs `antsRegistration` | — (always runs) |
| 5 | MPRAGE white matter segmentation | FSL `fast` | — (always runs) |
| 6 | Apply MPRAGE → DCE transform to WM mask | ANTs `antsApplyTransforms` | — (always runs) |
| 7 | VFA bias field correction (1st round) | FSL `fast` | `-b` |
| 8 | VFA z-axis normalization | `VFA_norm.py` | `-Z` |
| 9 | VFA bias field correction (2nd round) | FSL `fast` | `-B` |
| 10 | T1 map generation | ROCKETSHIP / MATLAB | — (always runs) |
| 11 | Apply MPRAGE → DCE transform to brain mask | ANTs `antsApplyTransforms` | — (always runs) |
| 12 | AIF selection | `AutoAIF` neural network | `-A` |
| 13 | DCE bias field correction | FSL `fast` | `-b` |
| 14 | DCE z-axis normalization | `DCE_norm.py` | `-Z` |

---

## Analysis (`DCE_all.sh`)

| Step | Name | Tool | Flag Required |
|---|---|---|---|
| 0 | DCE smoothing | `iNESMA_GPU.py` (CUDA) | `-S` |
| 1 | Ktrans mapping | ROCKETSHIP / MATLAB | — (always runs) |
| 2 | GM & CSF masking | ANTs + FSL `fslmaths` | — (always runs) |
| 2a | FreeSurfer WM parcellation | FreeSurfer | `-f` |
| 3 | QC analysis | `ktrans_analysis.py`, `ktrans_report.py` | — (always runs) |
| 4 | Case report generation | `case_report.py` | — (always runs) |
| 5 | Population report generation | `population_report.py` | — (always runs, after all cases) |

---

## External Tool Versions

| Tool | Version | Used In |
|---|---|---|
| HD-BET | latest | Step 1 |
| FSL | 6.0 | Steps 2, 5, 7, 9, 13 |
| ANTs | 2.6.2 | Steps 3, 4, 6, 11 |
| MATLAB | R2023a | Steps 10, 1 |
| ROCKETSHIP | 1.2 | Steps 10, 1 |
| FreeSurfer | 6.0 | Step 2a |
| Numba/CUDA | 13 | Step 0 |
