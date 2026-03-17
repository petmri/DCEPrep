# GPUfit Integration

DCEPrep uses [GPUfit](https://github.com/ironictoo/Gpufit), a CUDA-accelerated curve fitting library, to dramatically speed up the numerical model fitting that underlies both T1 mapping and DCE pharmacokinetic analysis. GPUfit implements the Levenberg-Marquardt algorithm on the GPU and exposes MATLAB MEX bindings that are called directly by ROCKETSHIP.

---

## What GPUfit Does in DCEPrep

GPU-based parallel fitting replaces CPU-bound iterative least-squares solvers. For large DCE datasets (hundreds of thousands of voxels), this can reduce fitting time from hours to minutes.

GPUfit is invoked at two points in the pipeline:

| Pipeline step | MEX file used | Purpose |
|---|---|---|
| Preprocessing Step 10 (T1 mapping) | `GpufitCudaAvailableMex.mexa64` | VFA-based T1 map generation via ROCKETSHIP |
| Analysis Step 1 (Ktrans fitting) | `GpufitConstrainedMex.mexa64` | Extended Tofts model fitting via ROCKETSHIP's `run_dce_cli` |

DCEPrep detects whether a GPU is available at runtime and records this in the per-case report. If GPUfit cannot find a CUDA-capable device it falls back to CPU fitting.

---

## Pharmacokinetic Models Supported

GPUfit (petmri fork) includes GPU-optimised implementations of:

- Extended Tofts (used by DCEPrep/ROCKETSHIP)
- Tofts
- Patlak
- Tissue Uptake
- Two-Compartment Exchange
- T1 FA Exponential

---

## How DCEPrep Locates GPUfit

DCEPrep searches for GPUfit's MEX files and MATLAB model definitions at startup:

```bash
# T1 mapping MEX (preprocess_all.sh)
GPUFIT_PATH=$(find $HOME -name 'GpufitCudaAvailableMex.mexa64' -printf '%h\n' -quit \
  || find / -name 'GpufitCudaAvailableMex.mexa64' -printf '%h\n' -quit)

# DCE analysis MEX (DCE_all.sh)
GPUFIT_PATH=$(find $HOME -name 'GpufitConstrainedMex.mexa64' -printf '%h\n' -quit \
  || find / -name 'GpufitConstrainedMex.mexa64' -printf '%h\n' -quit)

# MATLAB model ID definitions (both scripts)
GPUFIT_M_PATH=$(find $HOME -name 'ModelID.m' -printf '%h\n' -quit)
```

Both `GPUFIT_PATH` and `GPUFIT_M_PATH` are then passed to MATLAB via `addpath`:

```matlab
addpath '$GPUFIT_PATH';
addpath '$GPUFIT_M_PATH';
```

In Docker, GPUfit is installed at `/opt/Gpufit/` with MATLAB bindings at `/opt/Gpufit/matlab64/`, and the library path is set automatically:

```
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/Gpufit/matlab64/matlab
```

---

## Installing GPUfit Without Docker

Download the prebuilt Linux release:

```bash
wget https://github.com/ironictoo/Gpufit/releases/download/1.3/Gpufit_1.3.0_linux.zip
unzip Gpufit_1.3.0_linux.zip -d /opt/Gpufit
```

Ensure the `matlab64/` directory is reachable from `$HOME` so DCEPrep's path discovery can find the MEX files.

!!! warning "CUDA required"
    GPUfit requires a CUDA-capable NVIDIA GPU and a compatible CUDA toolkit. Without a GPU, ROCKETSHIP will fall back to CPU-based fitting, which is significantly slower on large datasets.

---

## GPU Detection in Reports

DCEPrep's case report (`case_report.py`) checks the MATLAB fit logs for the string `"Gpufit detected"` and includes GPU availability in the per-subject QC report. This helps identify runs where GPU acceleration was unavailable and fitting may have taken longer or used different numerical paths.

---

## Related Pages

- [ROCKETSHIP Integration](rocketship.md) — GPUfit is called through ROCKETSHIP's fitting scripts
- [GPUfit on GitHub](https://github.com/ironictoo/Gpufit)
