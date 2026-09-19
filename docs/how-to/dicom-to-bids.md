# DICOM to BIDS Conversion

Two paths convert raw DICOM data into the BIDS layout DCEPrep expects: the recommended automated [dce2bids](https://github.com/petmri/dce2bids) tool, or DCEPrep's bundled manual script, `sort_dicom.py`.

---

## Recommended: dce2bids

[dce2bids](https://github.com/petmri/dce2bids) converts the DCE, VFA, and one structural (T1 MPRAGE) series from a DICOM session into BIDS. Instead of maintaining a hand-edited series-matching config per site (as `sort_dicom.py` requires), dce2bids uses a coding agent (Claude Code, Codex, VS Code with Copilot, or Cursor) to work out the correct series-matching rules **once per scanner/protocol**, following the rules and validation steps defined in the tool's `SKILL.md`. After that one-time AI-assisted setup, converting each new participant is a single command with no AI involved.

---

### Requirements

- Linux environment (tested on Ubuntu 22.04; Mac/Windows via WSL2 is untested)
- A paid subscription to a coding agent capable of reading a `SKILL.md` file — Claude Code, Codex, VS Code with Copilot, or Cursor (tested with Claude Code, Opus 4.8 at high effort)

---

### One-Time Setup

```bash
git clone https://github.com/petmri/dce2bids.git
cd dce2bids
env/bootstrap.sh   # optional — the agent will run this for you if skipped
```

---

### Converting a New Scanner or Protocol (AI-Assisted)

Open your coding agent in the `dce2bids` folder, grant it access to your data folder, and ask it to convert your data, specifying the contrast agent used:

> Convert all the DICOMs in `/data/study-1/` to BIDS using dce2bids. The contrast agent **[contrast agent]** was used for all DCE scans.

---

### Verifying the Output

The agent will automatically run a full verification of the converted BIDS dataset. The full report is saved at `code/bids_status_report.txt`.

To re-run the verification without re-converting, use the `verify_bids.py` script:
```bash
scripts/verify_bids.py <your-bids-folder>
```
---

### Using dce2bids with DCEPrep

1. Run the dce2bids setup/conversion described above to produce a BIDS dataset.
2. Confirm `code/bids_status_report.txt` shows a clean result.
3. Point DCEPrep at the resulting BIDS directory as described in [BIDS Data Setup](../getting-started/bids-setup.md).

DCEPrep itself only consumes BIDS-organized data — it does not call dce2bids directly, so any BIDS dataset produced by dce2bids that matches the [required file patterns](../getting-started/bids-setup.md#required-files-per-subjectsession) will work.

---

## Legacy: sort_dicom.py

DCEPrep also ships a built-in script, `sort_dicom.py`, a wrapper around `dcm2bids` that converts raw DICOM files into a BIDS-compliant NIfTI structure using the project's `config.json` mapping.

---

### Prerequisites

- `dcm2bids` installed (`pip install dcm2bids`)
- `pydicom` installed (included in `venv_requirements.txt`)
- DICOM files organized by subject/session

---

### How It Works

`sort_dicom.py` reads DICOM series and maps them to BIDS entities using `config.json`. The config maps DICOM `SeriesDescription` patterns to BIDS filenames, covering:

- T1-weighted MPRAGE (`T1w`)
- FLAIR
- DCE series
- VFA images at multiple flip angles (2°, 5°, 10°, 12°, 15°, 20°, 25°)

---

### Running the Conversion

```bash
python sort_dicom.py \
    --input  /path/to/dicoms/sub-01/ses-01 \
    --output /path/to/rawdata \
    --subject 01 \
    --session 01
```

#### How `sort_dicom.py` works

The script is designed for batch processing. It:

1. Scans the source directory for subject folders
2. Detects session ID from the folder name (`_s2` suffix → session 02, otherwise session 01)
3. Expects each subject folder to contain exactly two subdirectories: `dicom/` and `log/`
4. Calls `dcm2bids` with `-d <dicom_dir> -p <subject_id> -s <session_id> -c config.json -o <output_dir>`
5. Moves log files into the BIDS `logs/` directory for that subject/session

!!! note
    The source and output directories are currently hardcoded in the script. Edit lines 13–14 of `sort_dicom.py` to point to your data locations before running.

#### Handling missing series

If a DICOM series does not match any pattern in `config.json`, `dcm2bids` places it in a `tmp_dcm2bids/` folder. Check this folder after conversion to see if any series were missed, and update `config.json` patterns if needed.

---

### The `config.json` Mapping

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

### Verifying the Output

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

### Troubleshooting

**Missing series after conversion**
:   Check the `tmp_dcm2bids/` folder for unconverted files. Compare the DICOM `SeriesDescription` with your `config.json` patterns. Use `dcm2bids_helper` to list all series descriptions in a DICOM directory.

**Wrong flip angle labels**
:   The flip angle entity (`flip-##`) is determined by the `config.json` mapping, not the DICOM `FlipAngle` field. If flip angles are mislabeled, update the `"SeriesDescription"` patterns in `config.json` to match your scanner's naming (e.g., `*FA2*` vs `*flip2*`).

**Duplicate or extra files**
:   `dcm2bids` may produce multiple files if a series description matches more than one config entry, or if the scanner splits a series. Check the `tmp_dcm2bids/` output and refine the `config.json` criteria (add `"SidecarFilename"` or other DICOM fields) to disambiguate.

**Session detection**
:   `sort_dicom.py` detects session 02 by looking for `_s2` (case-insensitive) in the folder name. All other folders are treated as session 01. Rename folders if your naming convention differs.
