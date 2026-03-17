# DICOM to BIDS Conversion

DCEPrep provides `sort_dicom.py`, a wrapper around `dcm2bids` that converts raw DICOM files into a BIDS-compliant NIfTI structure using the project's `config.json` mapping.

---

## Prerequisites

- `dcm2bids` installed (`pip install dcm2bids`)
- `pydicom` installed (included in `venv_requirements.txt`)
- DICOM files organized by subject/session

---

## How It Works

`sort_dicom.py` reads DICOM series and maps them to BIDS entities using `config.json`. The config maps DICOM `SeriesDescription` patterns to BIDS filenames, covering:

- T1-weighted MPRAGE (`T1w`)
- FLAIR
- DCE series
- VFA images at multiple flip angles (2°, 5°, 10°, 12°, 15°, 20°, 25°)

---

## Running the Conversion

```bash
python sort_dicom.py \
    --input  /path/to/dicoms/sub-01/ses-01 \
    --output /path/to/rawdata \
    --subject 01 \
    --session 01
```

!!! warning "Stub"
    The exact CLI arguments, batch processing options, and handling of missing series need to be documented here. Check `sort_dicom.py --help` for current usage.

---

## The `config.json` Mapping

The `config.json` file defines how DICOM series descriptions are matched to BIDS filenames. Open it to verify that your site's `SeriesDescription` values match the expected patterns:

```json
{
  "descriptions": [
    {
      "datatype": "anat",
      "suffix": "T1w",
      "criteria": {
        "SeriesDescription": "*MPRAGE*"
      }
    },
    {
      "datatype": "fmap",
      "suffix": "VFA",
      "custom_entities": "flip-2",
      "criteria": {
        "SeriesDescription": "*flip2*"
      }
    }
  ]
}
```

If your scanner uses different series names, edit the `"SeriesDescription"` patterns to match.

---

## Verifying the Output

After conversion, validate the BIDS dataset:

```bash
pip install bids-validator
bids-validator /path/to/rawdata
```

Then confirm the expected files exist before running DCEPrep:

```
rawdata/sub-01/ses-01/
├── anat/sub-01_ses-01_T1w.nii.gz
├── anat/sub-01_ses-01_T1w.json
├── fmap/sub-01_ses-01_flip-2_VFA.nii.gz
├── fmap/sub-01_ses-01_flip-5_VFA.nii.gz
└── fmap/sub-01_ses-01_DCE.nii.gz
```

---

## Troubleshooting

!!! warning "Stub"
    Common conversion issues (missing series, wrong flip angle labels, multi-echo data) and their solutions need to be added here.
