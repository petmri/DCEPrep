"""VFA_norm.py: slice normalization on synthetic volumes, and its failure reports.

Run from the repository root: python3 -m pytest tests
"""
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import VFA_norm  # noqa: E402

SHAPE = (64, 64, 8)
WM_INTENSITY = 500.0
PREFIX = "sub-01_ses-01"


def write_session(tmp_path, slice_gains, wm_slices=range(1, 7), wm_half_width=20, flip="01"):
    """Write a brain VFA and its white-matter-masked copy; return (anat dir, both paths).

    White matter is a centred square on `wm_slices`; every slice is scaled by its gain.
    """
    rng = np.random.default_rng(0)
    anat = tmp_path / "anat"
    anat.mkdir(exist_ok=True)
    volume = rng.normal(300.0, 15.0, SHAPE)
    wm_mask = np.zeros(SHAPE, dtype=bool)
    lo, hi = 32 - wm_half_width, 32 + wm_half_width
    for k in wm_slices:
        wm_mask[lo:hi, lo:hi, k] = True
    volume[wm_mask] = rng.normal(WM_INTENSITY, 15.0, int(wm_mask.sum()))
    volume *= np.asarray(slice_gains, dtype=float)[None, None, :]
    stem = f"{PREFIX}_flip-{flip}_space-DCEref"
    brain = anat / f"{stem}_label-brain_VFA.nii.gz"
    wm = anat / f"{stem}_label-WM_VFA.nii.gz"
    nib.save(nib.Nifti1Image(volume.astype(np.float32), np.eye(4)), brain)
    nib.save(nib.Nifti1Image((volume * wm_mask).astype(np.float32), np.eye(4)), wm)
    return anat, brain, wm, wm_mask


def test_slice_gains_are_removed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    gains = [1.0, 0.8, 1.0, 1.25, 1.0, 0.9, 1.1, 1.0]
    anat, brain, wm, wm_mask = write_session(tmp_path, gains)

    VFA_norm.normalize(str(brain), str(wm), str(anat), PREFIX)

    out = nib.load(anat / f"{PREFIX}_flip-01_space-DCEref_desc-bfcz_VFA.nii.gz").get_fdata()
    wm_means = np.array([out[:, :, k][wm_mask[:, :, k]].mean() for k in range(1, 7)])
    assert wm_means.std() / wm_means.mean() < 0.02
    # slices without white matter are left as they were
    original = nib.load(brain).get_fdata()
    np.testing.assert_allclose(out[:, :, 0], original[:, :, 0], rtol=1e-6)
    np.testing.assert_allclose(out[:, :, 7], original[:, :, 7], rtol=1e-6)


def test_empty_white_matter_names_the_registration(tmp_path, monkeypatch):
    """The 2026-10-27 ZeroDivisionError: a VFA registered off the white-matter mask."""
    monkeypatch.chdir(tmp_path)
    anat, brain, wm, _ = write_session(tmp_path, np.ones(8), wm_slices=[])

    with pytest.raises(VFA_norm.VFANormError, match="registration"):
        VFA_norm.normalize(str(brain), str(wm), str(anat), PREFIX)


def test_no_fittable_slice_names_the_registration(tmp_path, monkeypatch):
    """The 2026-10-27 'no median for empty data': every slice under the voxel minimum."""
    monkeypatch.chdir(tmp_path)
    # 20 x 20 = 400 white-matter voxels per slice, under the 1000 needed
    anat, brain, wm, _ = write_session(tmp_path, np.ones(8), wm_half_width=10)

    with pytest.raises(VFA_norm.VFANormError, match="largest slice: 400"):
        VFA_norm.normalize(str(brain), str(wm), str(anat), PREFIX)


def test_script_reports_the_reason_and_fails(tmp_path):
    """Run as preprocess_vfa_t1.sh runs it: one clear line on stderr, non-zero exit."""
    anat, _, _, _ = write_session(tmp_path, np.ones(8), wm_slices=[])

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "VFA_norm.py"), str(anat), PREFIX, "1"],
        cwd=tmp_path, capture_output=True, text=True,
    )

    assert result.returncode == 1
    assert "ERROR:" in result.stderr and "registration" in result.stderr
    assert "Traceback" not in result.stderr
