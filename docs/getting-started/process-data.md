# Process Data

This guide walks through a complete DCEPrep run from start to finish using Docker.

---

## Prerequisites

- Docker installed and running (see [Installation](installation.md#docker-recommended))
- MATLAB and FreeSurfer license files available
- BIDS-organized data (see [BIDS Data Setup](bids-setup.md))

---

## Step 1 — Point to your data

Edit `run_docker.sh` line 24 to point to your BIDS `rawdata` directory:

```bash
DATA_DIR="/path/to/your/bids/rawdata"
```

---

## Step 2 — Launch the container

```bash
./run_docker.sh
```

The container starts with DCEPrep's working directory as the current directory and your data directory mounted inside.

---

## Step 3 — Run preprocessing

```bash
./preprocess_all.sh -d /data/rawdata -b -Z -m
```

| Flag | What it does |
|---|---|
| `-d /data/rawdata` | Path to your BIDS rawdata folder (required) |
| `-b` | Bias field correction |
| `-Z` | Z-axis slice normalization |
| `-m` | Head motion correction |

For a first run on new data, add `-c` to start with a clean derivatives folder:

```bash
./preprocess_all.sh -d /data/rawdata -b -Z -m -c
```

---

## Step 4 — Run analysis

```bash
./DCE_all.sh -d /data/rawdata -s
```

| Flag | What it does |
|---|---|
| `-d /data/rawdata` | Path to your BIDS rawdata folder (required) |
| `-s` | Skip cases whose Ktrans maps already exist |

Add `-f` to enable FreeSurfer white matter parcellation for subregion analysis:

```bash
./DCE_all.sh -d /data/rawdata -s -f
```

---

## Step 5 — Review outputs

After the analysis completes, find your reports in each subject/session's derivatives folder:

```
derivatives/
└── sub-01/
    └── ses-01/
        ├── case_report.html       # Per-case QC report
        ├── dce/
        │   ├── sub-01_ses-01_Ktrans.nii
        │   └── sub-01_ses-01_vp.nii
        └── anat/
            └── sub-01_ses-01_space-DCEref_T1map.nii
```

A `population_report.html` is generated at the top of the derivatives tree once all cases finish.

---

## Common first-run example

This is a typical first run with all major corrections enabled and comparison mode to keep outputs labeled:

```bash
# Preprocess with bias correction, z-normalization, and auto AIF
./preprocess_all.sh -d /data/rawdata -b -c -Z -A -C fullPrep

# Analyze with FreeSurfer parcellation, skipping already-processed cases
./DCE_all.sh -d /data/rawdata -s -f -C fullPrep
```

---

## Next Steps

- [Full preprocessing options](../user-guide/preprocessing.md)
- [Full analysis options](../user-guide/analysis.md)
- [Understanding outputs](../user-guide/outputs.md)
- [AIF selection methods](../user-guide/aif-selection.md)
