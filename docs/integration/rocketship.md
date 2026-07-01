# ROCKETSHIP Integration

DCEPrep uses [ROCKETSHIP](https://github.com/petmri/ROCKETSHIP) (version 1.2+), a MATLAB-based DCE-MRI analysis framework, for two critical steps: T1 map generation and Ktrans pharmacokinetic modeling.

---

## What ROCKETSHIP Does in DCEPrep

| Pipeline step | ROCKETSHIP function | Script called |
|---|---|---|
| Preprocessing Step 10 | VFA-based T1 map generation | `run_dce_cli.m` |
| Analysis Step 1 | Ktrans / vp mapping (extended Tofts model) | `parametric_scripts/custom_scripts/T1mapping_fit.m` |

---

## How DCEPrep Locates ROCKETSHIP

DCEPrep finds the ROCKETSHIP installation at runtime by searching for `run_dce_cli.m`:

```bash
find / -name '*run_dce_cli.m' 2>/dev/null
```

In Docker, ROCKETSHIP is installed at a fixed path and the script preferences are mounted at:

```
/opt/ROCKETSHIP/ROCKETSHIP-dev/script_preferences.txt
```

When running without Docker, ensure the ROCKETSHIP directory containing `run_dce_cli.m` and the `parametric_scripts/` folder is accessible.

---

## Reproducibility

DCEPrep records the ROCKETSHIP git commit hash at analysis time and embeds it in case and population reports. This ensures computational reproducibility: you can identify exactly which version of ROCKETSHIP produced a given set of results.

---

## ROCKETSHIP Version

DCEPrep requires ROCKETSHIP **1.2** or later with the `parametric_scripts` add-on.

The GitHub Actions CI/CD workflow automatically clones the `petmri/ROCKETSHIP` repository (dev branch) before running tests:

```yaml
- uses: actions/checkout@v4
  with:
    repository: petmri/ROCKETSHIP
    ref: dev
```

---

## Script Preferences

ROCKETSHIP's behavior is configured via a `script_preferences.txt` file. In Docker, this is provided by DCEPrep's `docker/files/` directory and mounted at the expected location.

DCEPrep ships a default `script_preferences.txt` in `docker/files/`. Key settings:

### Input configuration

| Setting | Value | Description |
|---|---|---|
| `filevolume` | `1` | 4D NIfTI input |
| `dynamic_files` | `/dce/*_desc-bfcz_DCE.nii*` | Preprocessed DCE series |
| `t1map_files` | `/anat/*space-DCEref_T1map.nii*` | T1 map in DCE space |
| `roi_files` | `/anat/*space-DCEref_desc-brain_mask.nii*` | Brain mask ROI |
| `aif_files` | `/dce/*desc-AIF_T1map.nii*` | AIF T1 map |
| `start_t` | `3` | Skip first 2 timepoints |

### Pharmacokinetic model

| Setting | Value | Description |
|---|---|---|
| `quant` | `1` | Quantitative DCE (not semi-quantitative) |
| `patlak` | `1` | **Patlak model enabled** (2-parameter, no backflux) |
| `ex_tofts` | `0` | Extended Tofts disabled |
| `tofts` | `0` | Standard Tofts disabled |
| `auc` | `0` | Area-under-curve disabled |

### AIF and contrast agent

| Setting | Value | Description |
|---|---|---|
| `aif_rr_type` | `aif_roi` | Use provided AIF mask |
| `aif_type` | `1` | Fitted AIF |
| `hematocrit` | `0.45` | Default hematocrit |
| `relaxivity` | `2.8` | r1 relaxivity (mM⁻¹s⁻¹); auto-adjusted based on `AcquisitionDateTime` |
| `blood_t1` | `2.000` | Blood T1 in seconds |
| `injection_time` | `-2` | Auto-detect injection time |

### Processing

| Setting | Value | Description |
|---|---|---|
| `fit_voxels` | `1` | Voxel-wise fitting |
| `number_cpus` | `0` | Use all available CPU cores |
| `time_smoothing` | `none` | No temporal smoothing |
| `xy_smooth_size` | `0` | No spatial smoothing |
| `outputft` | `1` | NIfTI output |

---

## Installing ROCKETSHIP Without Docker

```bash
git clone https://github.com/petmri/ROCKETSHIP.git
cd ROCKETSHIP
git checkout v1.2   # or the appropriate release tag
```

Add the ROCKETSHIP directory to MATLAB's path, and ensure the `parametric_scripts/` subdirectory is also on the path.

---

## Related Projects

- [AutoAIF](auto-aif.md) — companion repo providing the neural network for automated AIF detection
- [GPUfit](gpufit.md) — CUDA-accelerated curve fitting used by ROCKETSHIP for T1 mapping and Ktrans fitting
- [ROCKETSHIP on GitHub](https://github.com/petmri/ROCKETSHIP)
