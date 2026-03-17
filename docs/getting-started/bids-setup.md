# BIDS Data Setup

DCEPrep requires data organized according to the [Brain Imaging Data Structure (BIDS)](https://bids-specification.readthedocs.io/) specification.

!!! warning "Stub article"
    This article is incomplete. Details on the exact BIDS layout, required JSON sidecar fields, and flip angle naming conventions need to be added.

---

## Overview

All input data must be BIDS-compliant NIfTI files with valid JSON sidecars. DCEPrep uses the filenames and BIDS entities (subject, session, flip angle) to locate and match images automatically.

---

## Required Files Per Subject/Session

| File Pattern | Description |
|---|---|
| `sub-##_ses-##_flip-##_VFA.nii.gz` | Variable Flip Angle images — one per flip angle |
| `sub-##_ses-##_DCE.nii.gz` | 4D Dynamic Contrast-Enhanced series |
| `sub-##_ses-##_T1w.nii.gz` | T1-weighted MPRAGE |

DCEPrep supports any number of VFA flip angles. The flip angle value is encoded in the `flip-##` BIDS entity.

---

## Expected Directory Structure

```
rawdata/
├── sub-01/
│   └── ses-01/
│       ├── anat/
│       │   ├── sub-01_ses-01_T1w.nii.gz
│       │   └── sub-01_ses-01_T1w.json
│       └── fmap/  (or perf/ — TBD)
│           ├── sub-01_ses-01_flip-2_VFA.nii.gz
│           ├── sub-01_ses-01_flip-5_VFA.nii.gz
│           ├── sub-01_ses-01_flip-10_VFA.nii.gz
│           └── sub-01_ses-01_DCE.nii.gz
└── sub-02/
    └── ...
```

!!! note
    The exact BIDS subfolder (anat, fmap, perf) for VFA and DCE files depends on your site's acquisition protocol. Confirm with the `config.json` used during DICOM conversion.

---

## Converting from DICOM

If your data is in DICOM format, use the included `sort_dicom.py` script to convert to BIDS:

```bash
python sort_dicom.py --input /path/to/dicoms --output /path/to/rawdata
```

See [DICOM to BIDS Conversion](../how-to/dicom-to-bids.md) for the full walkthrough.

---

## JSON Sidecar Requirements

!!! warning "Stub"
    The required JSON sidecar fields (e.g., `FlipAngle`, `RepetitionTime`, `EchoTime`) and their expected formats need to be documented here.

---

## Multi-Site Considerations

!!! warning "Stub"
    Notes on scanner-specific naming conventions, protocol differences across sites, and how the z-normalization and bias correction steps handle inter-scanner variability should be added here.

---

## Validating Your Dataset

Before running DCEPrep, validate your BIDS dataset with the [BIDS Validator](https://bids-standard.github.io/bids-validator/):

```bash
pip install bids-validator
bids-validator /path/to/rawdata
```

## Next Steps

- [Process Data guide](process-data.md)