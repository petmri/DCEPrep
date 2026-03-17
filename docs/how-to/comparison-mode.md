# Comparison Mode

Comparison mode (`-C [name]`) writes all outputs into a named subdirectory within each subject/session's derivatives folder. This lets you run the pipeline with different preprocessing options and compare outputs side-by-side without overwriting each other.

!!! warning "Stub article"
    This article needs real worked examples showing output differences and how to interpret them. Details on what files are copied vs. regenerated in comparison mode should also be added.

---

## How It Works

When `-C [name]` is passed:

- **Preprocessing:** All output files are written to `derivatives/sub-##/ses-##/<name>/` instead of directly under the session folder.
- **Analysis:** If a preprocessed run named `<name>` does not exist, essential files are copied from the standard (non-named) run before analysis proceeds.

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
derivatives/sub-01/ses-01/
├── withMC/
│   ├── anat/
│   └── dce/
└── noMC/
    ├── anat/
    └── dce/
```

---

## Example: Comparing Z-Normalization

!!! warning "Stub"
    Add a concrete example showing the effect of z-normalization on Ktrans values, with before/after report comparisons.

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
