# FreeSurfer White Matter Parcellation

The `-f` flag in `DCE_all.sh` enables FreeSurfer-based white matter parcellation, which divides the WM mask into anatomical subregions. This allows Ktrans to be analyzed separately in specific WM tracts and lobar regions rather than as a whole-brain average.

!!! warning "Stub article"
    This article needs details on which FreeSurfer atlas/parcellation is used, the specific WM subregions reported, how they map to the case/population reports, and any caveats about the required FreeSurfer version.

---

## Overview

Standard DCEPrep analysis computes Ktrans statistics for the whole WM mask. With `-f` enabled, FSL FAST segmentation is combined with FreeSurfer parcellation labels to subdivide WM into anatomically meaningful regions.

---

## Requirements

- FreeSurfer must be installed (Linux-centos6_x86_64-stable-pub-v6.0.0-2beb96c)
- FreeSurfer `license.txt` must be available (mounted in Docker)
- Sufficient disk space (~300 MB per subject for FreeSurfer outputs)

---

## Enabling Parcellation

```bash
./DCE_all.sh -d /data/rawdata -f
```

Parcellation runs as part of Step 2 (Gray Matter & CSF Masking) in the analysis pipeline.

---

## Parcellation Atlas

!!! warning "Stub"
    Document which FreeSurfer atlas is used (aparc, wmparc, etc.), how the labels are registered to DCE space, and which subregions appear in the outputs and reports.

---

## Output Subregions

!!! warning "Stub"
    List the specific WM subregions (e.g., frontal WM, parietal WM, corpus callosum) that appear in the case and population reports when `-f` is enabled.

---

## Run Time

FreeSurfer surface reconstruction is computationally expensive. Expect ~6–8 hours per subject on a standard workstation. The `-s` (skip) flag can be used to avoid re-running parcellation for already-processed cases.

!!! tip
    If you only need whole-brain WM Ktrans statistics, omit `-f` to save time. Parcellation adds significant runtime but provides subregion-level granularity.
