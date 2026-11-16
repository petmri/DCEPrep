#!/usr/bin/env python3
"""Check that the VFAs of a session were registered to the DCE consistently.

Each flip angle is registered to the DCE reference on its own. The VFAs are acquired back
to back in one scanner frame, so their rigid transforms should nearly agree. A flip whose
transform puts the brain somewhere else than the others did was mis-registered, and the T1
map fitted from that set is wrong even though nothing crashed.

The disagreement of a flip is how far its transform moves the corners of a 100 mm cube
around the registration centre, compared with the median position over all flips.

Usage:
    vfa_registration_qc.py ANAT_DIR [ANAT_DIR ...] [--max-mm MM] [--tsv out.tsv]

Reads ANAT_DIR/*_from-VFA*_to-DCEref.mat (antsRegistration rigid transforms) and prints one
line per session. It only reports unless --max-mm is given; then a flip that disagrees by
more than that is marked INCONSISTENT and the exit status is 1. There is no default
threshold: what counts as a failed registration is a study decision.
"""
import argparse
import itertools
import re
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

CUBE_HALF_WIDTH_MM = 50.0


def load_rigid(path):
    """Return (matrix, offset) of an ITK affine .mat so that y = matrix @ x + offset."""
    content = loadmat(str(path))
    keys = [key for key in content if "Transform" in key]
    if len(keys) != 1 or "fixed" not in content:
        raise ValueError(f"{path} is not an ITK affine transform file")
    parameters = np.asarray(content[keys[0]], dtype=float).ravel()
    if parameters.size != 12:
        raise ValueError(f"{path} holds {parameters.size} parameters, expected 12")
    matrix = parameters[:9].reshape(3, 3)
    centre = np.asarray(content["fixed"], dtype=float).ravel()
    return matrix, parameters[9:] + centre - matrix @ centre, centre


def flip_disagreement_mm(transform_paths):
    """Per flip: the largest distance of its mapped cube corners from the median over flips."""
    transforms = {}
    for path in transform_paths:
        flip = re.search(r"from-(VFA\d+)_to-", Path(path).name)
        transforms[flip.group(1) if flip else Path(path).name] = load_rigid(path)
    if len(transforms) < 2:
        raise ValueError("need the transforms of at least two flip angles")
    centre = np.median([t[2] for t in transforms.values()], axis=0)
    corners = centre + CUBE_HALF_WIDTH_MM * np.array(list(itertools.product((-1.0, 1.0), repeat=3)))
    mapped = {flip: corners @ matrix.T + offset for flip, (matrix, offset, _) in transforms.items()}
    median = np.median(np.stack(list(mapped.values())), axis=0)
    return {flip: float(np.linalg.norm(points - median, axis=1).max()) for flip, points in sorted(mapped.items())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("anat_dirs", nargs="+", type=Path)
    parser.add_argument("--max-mm", type=float, help="Largest disagreement that still passes; omit to report only.")
    parser.add_argument("--tsv", type=Path, help="Also write session, flip, disagreement_mm, status.")
    args = parser.parse_args(argv)

    rows = []
    failed = False
    for anat in args.anat_dirs:
        session = "/".join(part for part in anat.resolve().parts if part.startswith(("sub-", "ses-")))
        paths = sorted(anat.glob("*_from-VFA*_to-DCEref.mat"))
        try:
            disagreement = flip_disagreement_mm(paths)
        except ValueError as error:
            print(f"{session}: SKIPPED ({error})")
            rows.append((session, "", "", "skipped"))
            continue
        worst = max(disagreement, key=disagreement.get)
        limit = float("inf") if args.max_mm is None else args.max_mm
        ok = disagreement[worst] <= limit
        failed = failed or not ok
        detail = ", ".join(f"{flip} {mm:.1f}" for flip, mm in disagreement.items())
        verdict = "" if args.max_mm is None else ("ok " if ok else "INCONSISTENT ")
        print(f"{session}: {verdict}(mm from the median: {detail})")
        rows += [(session, flip, f"{mm:.2f}", "" if args.max_mm is None else ("ok" if mm <= limit else "inconsistent")) for flip, mm in disagreement.items()]
    if args.tsv:
        args.tsv.write_text("session\tflip\tdisagreement_mm\tstatus\n" + "".join("\t".join(row) + "\n" for row in rows))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
