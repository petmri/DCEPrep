# Comparison Mode

Comparison mode (`-C [name]`) writes all outputs into a named subdirectory within each subject/session's derivatives folder. This lets you run the pipeline with different preprocessing options and compare outputs side-by-side without overwriting each other.

---

## How It Works

When `-C [name]` is passed:

- **Preprocessing:** All output files are written to `derivatives/dceprep-<name>/sub-##/ses-##/` instead of the standard `derivatives/dceprep/` directory.
- **Analysis:** If a comparison run's preprocessed data does not exist, essential files (T1 maps, brain masks, registration transforms) are copied from the standard run before analysis proceeds. This avoids redundant computation for steps that are unchanged between comparisons.

### What gets copied vs. regenerated

| Copied from standard run | Regenerated in comparison run |
|---|---|
| Registration transforms (`.mat` files) | DCE preprocessing (bias correction, z-norm) |
| Brain masks | Ktrans maps |
| T1 maps (if unchanged) | QC reports |
| Segmentation masks | Population report |

---

## Example: Comparing Motion Correction

Run the pipeline twice — once with motion correction, once without:

```bash
# Run 1: with motion correction
./preprocess_all.sh -d /data/rawdata -b -Z -m -C withMC
./DCE_all.sh -d /data/rawdata -C withMC

# Run 2: without motion correction
./preprocess_all.sh -d /data/rawdata -b -Z -C noMC
./DCE_all.sh -d /data/rawdata -C noMC
```

Outputs land in:
```
derivatives/
├── dceprep-withMC/
│   └── sub-01/ses-01/
│       ├── anat/
│       └── dce/
└── dceprep-noMC/
    └── sub-01/ses-01/
        ├── anat/
        └── dce/
```

Compare the Ktrans maps and population reports between the two runs to assess the impact of motion correction on your dataset.

---

## Example: Comparing Z-Normalization

Test whether z-axis normalization improves inter-scanner consistency:

```bash
# Without z-normalization
./preprocess_all.sh -d /data/rawdata -b -C noZnorm
./DCE_all.sh -d /data/rawdata -C noZnorm

# With z-normalization
./preprocess_all.sh -d /data/rawdata -b -Z -C withZnorm
./DCE_all.sh -d /data/rawdata -C withZnorm
```

Compare the population reports: the z-normalized run should show reduced variance in Ktrans across subjects scanned on different machines.

---

## Targeting Specific Subjects

Use `-T` alongside `-C` to run comparison mode on a subset of subjects:

```bash
./preprocess_all.sh -d /data/rawdata -b -Z -C withZ -T sub-01/ses-01
```

---

## Notes

- Comparison mode does **not** require a clean run (`-c`); both named runs can coexist.
- The population report will aggregate whichever run is active — pass `-C [name]` to `DCE_all.sh` to report on a specific comparison.
