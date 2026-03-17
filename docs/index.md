# DCEPrep

**A preprocessing and analysis pipeline for Dynamic Contrast-Enhanced (DCE) MRI data.**

DCEPrep handles the full workflow for measuring permeability (Ktrans) from DCE-MRI acquisitions — from raw DICOM to publication-ready QC reports.

![Overview of DCEPrep processing steps](overview.png)

---

## What Does DCEPrep Do?

DCEPrep takes BIDS-organized MRI data and runs a two-phase pipeline:

**Phase 1 — Preprocessing (`preprocess_all.sh`)**
Prepares raw DCE and VFA images for kinetic modeling. Steps include brain extraction, image registration, bias field correction, z-axis normalization, T1 mapping, and arterial input function (AIF) selection.

**Phase 2 — Analysis (`DCE_all.sh`)**
Runs pharmacokinetic modeling via [ROCKETSHIP](integration/rocketship.md) to produce Ktrans permeability maps, then generates per-case and population-level HTML/PDF QC reports.

---

## Key Features

- **Fully scriptable** — driven by two shell scripts with straightforward CLI flags
- **BIDS-native** — expects and produces BIDS-compliant data structures
- **Docker-first** — a single container bundles FSL, ANTs, FreeSurfer, MATLAB, and ROCKETSHIP
- **Automated AIF** — optional neural-network-based arterial input function detection
- **Variance Reduction** — z-axis normalization and bias correction designed to reduce scanner variability
- **Automated QC** — per-case and population HTML reports with outlier detection
- **GPU acceleration** — Several steps utilize optional CUDA-based acceleration for faster processing

---

## How DCEPrep Fits In

DCEPrep is part of the **petmri** processing ecosystem. It sits downstream of DICOM conversion and upstream of group-level statistical analysis:

```mermaid
flowchart TD
    A[DICOM acquisition]
    B["BIDS conversion\nsort_dicom.py + dcm2bids"]
    G[Group-level statistics]

    subgraph DCEPrep["DCEPrep"]
        PRE["preprocess_all.sh\n─────────────────\n○  Bias field correction\n○  Image Registration\n○  Intensity Normalization\n○  Motion Correction\n○  T1 mapping\n○  AIF selection\n○  QC reports"]
        ANA["DCE_all.sh\n─────────────────\n○  Ktrans fitting w/ ROCKETSHIP\n○  QC reports\n○  Population-level summaries"]
        PRE --> ANA
    end

    A --> B --> PRE
    ANA --> G

    style A fill:#757575,stroke:#555,color:#fff
    style B fill:#F9A825,stroke:#F57F17,color:#000
    style G fill:#757575,stroke:#555,color:#fff
    style PRE fill:#C8DCEE,stroke:#7AAAC8,color:#1a2a3a
    style ANA fill:#C8DCEE,stroke:#7AAAC8,color:#1a2a3a
```

| Color | Meaning |
|---|---|
| Blue | Handled by DCEPrep |
| Amber | Partially supported (`sort_dicom.py` wraps dcm2bids) |
| Gray | Outside DCEPrep scope |

See [ROCKETSHIP Integration](integration/rocketship.md) for details on the MATLAB dependency.

---

## Quick Links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [Preprocessing Pipeline](user-guide/preprocessing.md)
- [Analysis Pipeline](user-guide/analysis.md)
- [CLI Reference — Preprocessing](reference/preprocessing-cli.md)
- [CLI Reference — Analysis](reference/analysis-cli.md)

---

## Citation

If you use DCEPrep in your research, please cite:

> Barnes S, et al. Automated DCE-MRI processing with DCEPrep for Blood-Brain Barrier permeability in a multi-site aging study. *Pending*. 2026.
