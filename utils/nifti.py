import os

import nibabel as nib
import numpy as np


def nifti_stem(path):
    if path.endswith('.nii.gz'):
        return path[:-7]
    if path.endswith('.nii'):
        return path[:-4]
    return os.path.splitext(path)[0]


def resolve_nifti_path(path):
    candidates = [path]
    if path.endswith('.nii.gz'):
        candidates.append(path[:-3])
    elif path.endswith('.nii'):
        candidates.append(path + '.gz')

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    return path


def first_existing_nifti_path(*paths):
    for path in paths:
        resolved_path = resolve_nifti_path(path)
        if os.path.exists(resolved_path):
            return resolved_path

    return paths[0]


def load_nifti_float32(path):
    image = nib.load(resolve_nifti_path(path))
    data = np.asarray(image.dataobj, dtype=np.float32)
    return nib.Nifti1Image(data, image.affine, image.header)