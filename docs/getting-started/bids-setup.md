# BIDS Data Setup

DCEPrep requires data organized according to the [Brain Imaging Data Structure (BIDS)](https://bids-specification.readthedocs.io/) specification.

---

## Overview

All input data must be BIDS-compliant NIfTI files with valid JSON sidecars. DCEPrep uses the filenames and BIDS entities (subject, session, flip angle) to locate and match images automatically.

---

## Required Files Per Subject/Session

| File Pattern | Description |
|---|---|
| `sub-##_ses-##_flip-##_VFA.nii.gz` | Variable Flip Angle images — one per flip angle (e.g., `flip-2`, `flip-5`, `flip-10`, `flip-15`) |
| `sub-##_ses-##_flip-##_VFA.json` | JSON sidecar for each VFA image |
| `sub-##_ses-##_DCE.nii.gz` | 4D Dynamic Contrast-Enhanced series |
| `sub-##_ses-##_DCE.json` | JSON sidecar for the DCE series |
| `sub-##_ses-##_T1w.nii.gz` | T1-weighted MPRAGE |
| `sub-##_ses-##_T1w.json` | JSON sidecar for the T1w image |

DCEPrep supports any number of VFA flip angles. The flip angle value is encoded in the `flip-##` BIDS entity (the integer degree value, e.g., `flip-2` for 2°, `flip-15` for 15°).

**Optional files:**

| File Pattern | Description |
|---|---|
| `sub-##_ses-##_desc-AIF_mask.nii.gz` | Manually drawn AIF mask (required when not using `-A` automatic mode) |
| `sub-##_ses-##_FLAIR.nii.gz` | FLAIR image (used in case report if available) |

---

## Expected Directory Structure

```
rawdata/
├── sub-01/
│   └── ses-01/
│       ├── anat/
│       │   ├── sub-01_ses-01_T1w.nii.gz
│       │   └── sub-01_ses-01_T1w.json
│       └── fmap/
│           ├── sub-01_ses-01_flip-2_VFA.nii.gz
│           ├── sub-01_ses-01_flip-2_VFA.json
│           ├── sub-01_ses-01_flip-5_VFA.nii.gz
│           ├── sub-01_ses-01_flip-5_VFA.json
│           ├── sub-01_ses-01_flip-10_VFA.nii.gz
│           ├── sub-01_ses-01_flip-10_VFA.json
│           ├── sub-01_ses-01_DCE.nii.gz
│           └── sub-01_ses-01_DCE.json
└── sub-02/
    └── ...
```

!!! note
    The BIDS subfolder for VFA and DCE files may vary by site (commonly `fmap/` or `perf/`). Confirm with the `config.json` used during DICOM conversion. DCEPrep searches for files by name pattern, so the subfolder choice does not affect pipeline operation.

---

## Converting from DICOM

If your data is in DICOM format, use the included `sort_dicom.py` script to convert to BIDS:

!!! note
    `sort_dicom.py` must be edited to specify local paths, and is designed to work with DICOMs organized in a specific way (see [DICOM to BIDS Conversion](../how-to/dicom-to-bids.md) for details). Ensure your DICOMs are structured correctly before running the script.

```bash
python sort_dicom.py
```

The script reads source directories from hardcoded paths and calls `dcm2bids` with the project's `config.json`. See [DICOM to BIDS Conversion](../how-to/dicom-to-bids.md) for the full walkthrough.

---

## JSON Sidecar Requirements

Each NIfTI file should have a matching `.json` sidecar containing acquisition parameters. DCEPrep and ROCKETSHIP read these fields at runtime:

| Field | Required for | Example | Notes |
|---|---|---|---|
| `FlipAngle` | VFA, DCE | `15` | Degrees; used for T1 mapping and Ktrans fitting |
| `RepetitionTime` | VFA, DCE | `0.00536` | Seconds; overrides ROCKETSHIP's default TR |
| `EchoTime` | VFA, DCE | `0.00193` | Seconds |
| `AcquisitionDateTime` | DCE | `"2023-05-15T10:30:00"` | Used to auto-select contrast agent relaxivity (pre/post Oct 2017) |
| `MagneticFieldStrength` | Informational | `3` | Tesla; included in QC reports |
| `Manufacturer` | Informational | `"Siemens"` | Included in QC reports |
| `InstitutionName` | Informational | `"USC"` | Included in QC reports |

!!! tip
    `dcm2bids` automatically populates these fields from DICOM headers during conversion. If converting manually, ensure at minimum `FlipAngle` and `RepetitionTime` are present.

---

## Multi-Site Considerations

When processing data from multiple scanners or sites:

- **Scanner variability:** Different scanners produce different signal intensity profiles. DCEPrep's z-axis normalization (`-Z` flag) and bias field correction (`-b`, `-B` flags) are designed to reduce this inter-scanner variability by normalizing each z-slice to a consistent intensity distribution.
- **Contrast agent:** ROCKETSHIP auto-selects relaxivity based on `AcquisitionDateTime` (MultiHance before Oct 2017, Dotarem after). Override with `force_use_default_relaxivity = 1` in `script_preferences.txt` if your site uses a different agent.
- **Series descriptions:** Each site may use different DICOM `SeriesDescription` values. Edit the `config.json` mapping to match your site's naming conventions before running `sort_dicom.py`.
- **Flip angle sets:** Different sites may acquire different VFA flip angle sets. DCEPrep handles any number of flip angles automatically.

---

## Validating Your Dataset

Before running DCEPrep, validate your BIDS dataset with the [BIDS Validator](https://bids-standard.github.io/bids-validator/):

```bash
pip install bids-validator
bids-validator /path/to/rawdata
```

!!! note
    The BIDS validator may flag VFA and DCE files as non-standard since DCE-MRI is not yet fully specified in the BIDS standard. These warnings can be safely ignored as long as the file naming conventions above are followed.

## Next Steps

- [Process Data guide](process-data.md)