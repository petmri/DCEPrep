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

!!! warning "Stub"
    The specific ROCKETSHIP script preference settings used by DCEPrep (model selection, convergence criteria, fitting options) should be documented here.

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

- [vascular_function](vascular-function.md) — companion repo providing the neural network for automated AIF detection
- [GPUfit](gpufit.md) — CUDA-accelerated curve fitting used by ROCKETSHIP for T1 mapping and Ktrans fitting
- [ROCKETSHIP on GitHub](https://github.com/petmri/ROCKETSHIP)
