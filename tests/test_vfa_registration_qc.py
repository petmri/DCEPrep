"""vfa_registration_qc.py on synthetic ITK transform files."""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vfa_registration_qc as qc  # noqa: E402


def rotation_z(degrees):
    a = np.radians(degrees)
    return np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])


def write_transform(anat, flip, translation=(0.0, 0.0, 0.0), matrix=np.eye(3), centre=(10.0, -20.0, 30.0)):
    """An antsRegistration-style rigid .mat: parameters = matrix then translation, fixed = centre."""
    anat.mkdir(parents=True, exist_ok=True)
    path = anat / f"sub-01_ses-01_from-VFA{flip:02d}_to-DCEref.mat"
    parameters = np.concatenate([np.asarray(matrix).ravel(), np.asarray(translation, dtype=float)])
    savemat(str(path), {"AffineTransform_double_3_3": parameters[:, None], "fixed": np.asarray(centre, dtype=float)[:, None]}, format="4")
    return path


def test_identical_transforms_agree(tmp_path):
    paths = [write_transform(tmp_path, flip, translation=(1.0, 2.0, 3.0)) for flip in (1, 2, 4, 6)]
    assert qc.flip_disagreement_mm(paths) == pytest.approx({"VFA01": 0.0, "VFA02": 0.0, "VFA04": 0.0, "VFA06": 0.0})


def test_one_flip_shifted_along_z_stands_out(tmp_path):
    """The RIDER case: one flip registered 12 mm off, the other three together."""
    paths = [write_transform(tmp_path, 1, translation=(0.0, 0.0, -12.0))]
    paths += [write_transform(tmp_path, flip, translation=(0.0, 0.0, 0.3 * flip)) for flip in (2, 4, 6)]
    disagreement = qc.flip_disagreement_mm(paths)
    # z shifts are -12, 0.6, 1.2, 1.8: the median is 0.9, so the stray flip is 12.9 mm away
    assert disagreement["VFA01"] == pytest.approx(12.9, abs=0.01)
    assert max(disagreement[f] for f in ("VFA02", "VFA04", "VFA06")) == pytest.approx(0.9, abs=0.01)


def test_a_rotation_counts_at_the_edge_of_the_brain(tmp_path):
    paths = [write_transform(tmp_path, flip) for flip in (1, 2, 3)]
    paths.append(write_transform(tmp_path, 4, matrix=rotation_z(5.0)))
    disagreement = qc.flip_disagreement_mm(paths)
    # a 5 degree turn moves a point 70.7 mm from the axis by 2 * 70.7 * sin(2.5 deg) = 6.2 mm
    assert disagreement["VFA04"] == pytest.approx(6.17, abs=0.05)
    assert disagreement["VFA01"] == pytest.approx(0.0, abs=1e-9)


def test_command_line_reports_and_fails_on_inconsistency(tmp_path, capsys):
    good = tmp_path / "sub-01/ses-01/anat"
    bad = tmp_path / "sub-01/ses-02/anat"
    for flip in (1, 2, 3):
        write_transform(good, flip)
        write_transform(bad, flip, translation=(0.0, 0.0, -10.0 if flip == 1 else 0.0))
    empty = tmp_path / "sub-02/ses-01/anat"
    empty.mkdir(parents=True)

    # without a threshold it reports and passes: the threshold is a study decision
    assert qc.main([str(bad)]) == 0
    assert "INCONSISTENT" not in capsys.readouterr().out

    code = qc.main([str(good), str(bad), str(empty), "--max-mm", "3", "--tsv", str(tmp_path / "qc.tsv")])
    out = capsys.readouterr().out

    assert code == 1
    assert "sub-01/ses-02: INCONSISTENT" in out and "sub-01/ses-01: ok" in out and "sub-02/ses-01: SKIPPED" in out
    lines = (tmp_path / "qc.tsv").read_text().splitlines()
    assert "sub-01/ses-02\tVFA01\t10.00\tinconsistent" in lines
    assert qc.main([str(bad), "--max-mm", "15"]) == 0
