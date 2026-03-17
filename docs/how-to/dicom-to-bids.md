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

### How `sort_dicom.py` works

The script is designed for batch processing. It:

1. Scans the source directory for subject folders
2. Detects session ID from the folder name (`_s2` suffix → session 02, otherwise session 01)
3. Expects each subject folder to contain exactly two subdirectories: `dicom/` and `log/`
4. Calls `dcm2bids` with `-d <dicom_dir> -p <subject_id> -s <session_id> -c config.json -o <output_dir>`
5. Moves log files into the BIDS `logs/` directory for that subject/session

!!! note
    The source and output directories are currently hardcoded in the script. Edit lines 13–14 of `sort_dicom.py` to point to your data locations before running.

### Handling missing series

If a DICOM series does not match any pattern in `config.json`, `dcm2bids` places it in a `tmp_dcm2bids/` folder. Check this folder after conversion to see if any series were missed, and update `config.json` patterns if needed.

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

**Missing series after conversion**
:   Check the `tmp_dcm2bids/` folder for unconverted files. Compare the DICOM `SeriesDescription` with your `config.json` patterns. Use `dcm2bids_helper` to list all series descriptions in a DICOM directory.

**Wrong flip angle labels**
:   The flip angle entity (`flip-##`) is determined by the `config.json` mapping, not the DICOM `FlipAngle` field. If flip angles are mislabeled, update the `"SeriesDescription"` patterns in `config.json` to match your scanner's naming (e.g., `*FA2*` vs `*flip2*`).

**Duplicate or extra files**
:   `dcm2bids` may produce multiple files if a series description matches more than one config entry, or if the scanner splits a series. Check the `tmp_dcm2bids/` output and refine the `config.json` criteria (add `"SidecarFilename"` or other DICOM fields) to disambiguate.

**Session detection**
:   `sort_dicom.py` detects session 02 by looking for `_s2` (case-insensitive) in the folder name. All other folders are treated as session 01. Rename folders if your naming convention differs.
