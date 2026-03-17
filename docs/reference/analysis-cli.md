# Analysis CLI Reference

Full reference for `DCE_all.sh`.

## Usage

```bash
./DCE_all.sh -d <rawdata_path> [options]
```

---

## Flags

| Flag | Argument | Required | Description |
|---|---|---|---|
| `-d` | `path` | **Yes** | Path to BIDS raw data directory. |
| `-C` | `name` | No | Enable [comparison mode](../how-to/comparison-mode.md). If a preprocessed run named `<name>` does not exist, copies essential files from the standard run. |
| `-f` | — | No | Enable FreeSurfer white matter parcellation for subregion Ktrans analysis. See [FreeSurfer Parcellation](../how-to/freesurfer-parcellation.md). |
| `-s` | — | No | Skip cases where the Ktrans output file already exists. |
| `-S` | — | No | Enable iNESMA smoothing of the DCE input before Ktrans fitting. Requires a CUDA GPU. |
| `-T` | `dir_path` | No | Target specific subject(s)/session(s). Default: `sub-*/ses-*/`. Accepts glob patterns or explicit paths. |

---

## Example Invocations

### Minimal run
```bash
./DCE_all.sh -d /data/rawdata
```

### Skip already-processed cases
```bash
./DCE_all.sh -d /data/rawdata -s
```

### With FreeSurfer parcellation, skip completed
```bash
./DCE_all.sh -d /data/rawdata -s -f
```

### With iNESMA smoothing (GPU required)
```bash
./DCE_all.sh -d /data/rawdata -S
```

### Comparison mode
```bash
./DCE_all.sh -d /data/rawdata -s -C noMC
```

### Target a single subject
```bash
./DCE_all.sh -d /data/rawdata -T sub-01/ses-01
```
