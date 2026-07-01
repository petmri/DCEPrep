# Preprocessing CLI Reference

Full reference for `preprocess_all.sh`.

## Usage

```bash
./preprocess_all.sh -d <rawdata_path> [options]
```

---

## Flags

| Flag | Argument | Required | Description |
|---|---|---|---|
| `-d` | `rawdata_path` | **Yes** | Path to BIDS raw data folder. |
| `-a` | `suffix` | No | AIF mask file suffix (default: `desc-AIF_mask`). `.nii.gz` is appended automatically. |
| `-A` | `mode` | No | Enable AutoAIF. Mode: `A` = fully automatic, `M` = manual if available else auto, `T` = manual + training data generation. Requires the [AutoAIF repo](https://github.com/petmri/AutoAIF). |
| `-b` | — | No | Enable **first round** of bias field correction on VFA and DCE images. |
| `-B` | — | No | Enable **second round** of bias field correction (applied after z-normalization). Only relevant when `-Z` is also set. |
| `-c` | — | No | Clean the case's derivatives folder before processing. Ensures a fresh run; disables skip behavior. |
| `-C` | `name` | No | Enable [comparison mode](../how-to/comparison-mode.md). Writes outputs to `derivatives/sub-##/ses-##/<name>/`. |
| `-m` | — | No | Enable head motion correction using FSL `mcflirt`. |
| `-s` | — | No | Skip preprocessing if the final DCE output file already exists. |
| `-t` | — | No | Run only up to T1 map generation (skip DCE processing). Useful for T1-only protocols. |
| `-T` | `dir_path` | No | Target specific subject(s)/session(s). Default: `sub-*/ses-*/`. Accepts glob patterns or explicit paths. |
| `-w` | `path` | No | Path to the AutoAIF neural network weights file. |
| `-Z` | — | No | Enable z-axis slice normalization on VFA and DCE images. |

---

## Example Invocations

### Minimal run (bias correction only)
```bash
./preprocess_all.sh -d /data/rawdata -b
```

### Full preprocessing with all corrections
```bash
./preprocess_all.sh -d /data/rawdata -b -B -Z -m -c
```

### With automatic AIF detection
```bash
./preprocess_all.sh -d /data/rawdata -b -Z -A A -w /opt/AutoAIF/weights.h5
```

### Target a single subject, comparison mode
```bash
./preprocess_all.sh -d /data/rawdata -b -Z -T sub-01/ses-01 -C withZ
```

### T1 mapping only
```bash
./preprocess_all.sh -d /data/rawdata -b -t
```
