# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DCEPrep is a DCE-MRI preprocessing and analysis pipeline that produces Ktrans/vp parametric maps and automated QC reports. It orchestrates external neuroimaging tools (FSL, ANTs, ROCKETSHIP/MATLAB, FreeSurfer) via bash scripts and uses Python for normalization, analysis, and report generation.

## Running the Pipeline

**Preprocessing** (VFA T1 mapping → bias correction → AIF selection):
```bash
./preprocess_all.sh -d /path/to/bids_data -b -c -Z -A -C noMC
```

**Analysis** (Ktrans mapping → QC reports):
```bash
./DCE_all.sh -d /path/to/bids_data -s -C noMC
```

**Docker** (encapsulates all dependencies):
```bash
./run_docker.sh
# or pull manually: docker pull lsaca05/dce:R2022a-dev
```

**Python environment** (non-Docker):
```bash
python3 -m venv tf && source tf/bin/activate
pip install -r venv_requirements.txt
```

## Documentation

```bash
mkdocs serve   # local preview at localhost:8000
mkdocs build   # build static site to site/
```

Deployed at: https://petmri.github.io/DCEPrep

## Architecture

Data flows in two stages:

```
BIDS Input
  → preprocess_all.sh
      ├─ Brain extraction + registration (ANTs, FSL)
      ├─ VFA/DCE normalization (VFA_norm.py, DCE_norm.py)
      ├─ T1 mapping (ROCKETSHIP via MATLAB)
      └─ AIF extraction (vascular_function neural network / manual)
  → DCE_all.sh
      ├─ Ktrans fitting (ROCKETSHIP via MATLAB)
      ├─ Tissue masking (ANTs + FSL)
      ├─ QC analysis (ktrans_analysis.py, ktrans_report.py)
      └─ Report generation (case_report.py → population_report.py)
```

**Key design points:**
- Bash scripts orchestrate all external tool calls; Python handles analysis and reporting only
- BIDS-compliant I/O throughout (`sub-*/ses-*/` directory structure)
- `-s` flag skips stages where outputs already exist (resume-safe)
- `-C [name]` comparison mode runs pipeline variants into separate output directories
- `-T [path]` targets a specific subject/session instead of batch processing
- `population_report.py` uses `ThreadPoolExecutor` for concurrent report generation

## Python Modules

| File | Purpose |
|------|---------|
| `VFA_norm.py` | Z-slice intensity normalization for VFA data (double Gaussian fitting) |
| `DCE_norm.py` | Z-slice normalization for 4D DCE data |
| `ktrans_analysis.py` | Slice-by-slice Ktrans statistics per tissue (WM, GM, CSF) |
| `ktrans_report.py` | Visualization: AIF curves, motion displacement, DCE temporal plots |
| `case_report.py` | Per-subject HTML report (Jinja2 + nilearn + CairoSVG) |
| `population_report.py` | Cohort-level HTML/PDF report with outlier tracking across 19 tissue regions |
| `aif_metric.py` | 8 AIF quality metrics; `quality_ultimate()` is the composite score |
| `iNESMA_GPU.py` | CUDA kernel for non-local neighborhood smoothing |
| `max_disp.py` | FSL mcflirt displacement magnitude calculation |
| `sort_dicom.py` | DICOM archiving/conversion (USC-PPG study, hard-coded paths) |
| `utils/constants.py` | Shared constants (`KTRANS_MIN_THRESHOLD = 1e-5`) |

Templates for HTML reports: `template.html` (case), `population_template.html` (cohort).

## External Dependencies

| Tool | Used For |
|------|---------|
| ROCKETSHIP + parametric_scripts | T1 mapping and Ktrans fitting (MATLAB) |
| FSL 6.0 | Brain extraction, tissue segmentation, motion correction |
| ANTs | Image registration |
| FreeSurfer | Optional WM parcellation (`-f` flag in DCE_all.sh) |
| HD-BET | Brain extraction (Python/PyTorch) |
| vascular_function | AutoAIF neural network (`-A A` mode) |

`config.json` defines DICOM→BIDS classification rules (VFA flip angles, DCE, T1w, FLAIR sequences) used by `sort_dicom.py` with `dcm2niix -b y -ba n -z y`.
