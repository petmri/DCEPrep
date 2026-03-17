# vascular_function Integration

DCEPrep uses [vascular_function](https://github.com/petmri/vascular_function), a companion repository from the petmri group, to perform automated Arterial Input Function (AIF) detection via a pre-trained deep learning model.

---

## What vascular_function Does in DCEPrep

The AIF describes the concentration of contrast agent in blood over time and is required for pharmacokinetic modeling. Selecting the AIF manually from DCE-MRI data is time-consuming and operator-dependent. vascular_function provides a neural network (`main_vif.py`) that identifies arterial voxels automatically from the DCE image.

DCEPrep calls vascular_function during **Preprocessing Step 12** when the `-A` flag is passed to `preprocess_all.sh`.

| Mode | Flag | Behavior |
|---|---|---|
| Automatic | `-A A` | Neural network selects AIF; no manual input needed |
| Manual-preferred | `-A M` | Uses manual mask if present, falls back to automatic |
| Training | `-A T` | Uses manual mask and generates training data for the model |

---

## Outputs

vascular_function produces the following files per subject:

| File | Description |
|---|---|
| `*_desc-AIFfloat_mask.nii` | Continuous probability mask of arterial voxels |
| `*_desc-AIFtopvoxels_mask.nii` | Thresholded binary mask (top voxels selected) |
| `*_desc-AIF_resampledcurve.svg` | Plot of the resampled AIF curve |
| `*_desc-AIF_mask.svg` | Visualization of the AIF mask overlaid on the image |

---

## How DCEPrep Locates vascular_function

At runtime DCEPrep searches for `main_vif.py`:

```bash
AUTO_AIF_PATH=$(find $HOME -wholename '*main_vif.py' -printf '%h\n' -quit \
  || find / -name '*main_vif.py' -printf '%h\n' -quit)
```

In Docker, vascular_function is installed at `/opt/vascular_function` and the pre-trained model weights are mounted at:

```
/opt/vascular_function/docker/files/model_weight_huber1.h5
```

---

## Installing vascular_function Without Docker

```bash
git clone https://github.com/petmri/vascular_function.git
pip install -r vascular_function/requirements.txt
```

!!! note
    The Docker installation filters out `cupy` and `tensorrt_cu12` to avoid GPU library conflicts. If installing manually in a GPU environment, review the requirements file and adjust CUDA-dependent packages for your setup.

Ensure `main_vif.py` is discoverable from your `$HOME` directory, or set `AUTO_AIF_PATH` manually before running `preprocess_all.sh`.

---

## Related Pages

- [AIF Selection](../user-guide/aif-selection.md) — full walkthrough of AIF selection modes
- [vascular_function on GitHub](https://github.com/petmri/vascular_function)
