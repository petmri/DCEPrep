# Installation

DCEPrep can be run via Docker (recommended) or installed directly on your system.

---

## Docker (Recommended)

Docker bundles all dependencies — FSL, ANTs, FreeSurfer, MATLAB, ROCKETSHIP, and the Python environment — into a single ~18 GB image. This is the easiest and most reproducible way to run DCEPrep.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running
- A valid **MATLAB license** file
- A valid **FreeSurfer license** file (`license.txt`)
- Your BIDS data directory accessible on the host

### 1. Clone the repository

```bash
git clone https://github.com/petmri/DCEPrep.git
cd DCEPrep
```

The `main` branch is stable. For a pinned release, check out a specific tag:

```bash
git checkout v1.0.0
```

### 2. Configure `run_docker.sh`

Open `run_docker.sh` and edit **line 24** to set the path to your data directory on the host machine.

### 3. Run

```bash
./run_docker.sh
```

This script will pull the image if it isn't already cached and launch a container with the correct mounts.

### Available image tags

Images are available on Docker Hub for multiple MATLAB releases:

```bash
docker pull lsaca05/dce:<MATLAB_release>-<branch>

# Examples:
docker pull lsaca05/dce:R2023a-main
docker pull lsaca05/dce:R2022a-dev
```

See [Docker Hub](https://hub.docker.com/repository/docker/lsaca05/dce/tags) for all available tags.

!!! note "Required mounts"
    The following paths must be shared with the container (handled automatically by `run_docker.sh`):

    - MATLAB license file
    - FreeSurfer `license.txt`
    - Your data directory
    - Script preferences folder (`docker/files/`)
    - `/etc/`

---

## Without Docker

If you prefer to run DCEPrep directly without a container, you must install all dependencies manually.

### Python environment

```bash
cd DCEPrep
python3 -m venv tf
source tf/bin/activate
pip install -r venv_requirements.txt
```

`conda` is also supported — install packages from `venv_requirements.txt` into a conda environment.

!!! tip
    `venv_requirements.txt` contains fully pinned versions including deep dependencies (TensorFlow, NVIDIA CUDA libraries). For a minimal install without GPU support, use `requirements.txt` instead.

### System dependencies

The following tools must be installed and available in your `PATH`:

| Tool | Required Version |
|---|---|
| [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation) | 6.0 |
| [ANTs](http://stnava.github.io/ANTs/) | 2.6.2 |
| [FreeSurfer](https://surfer.nmr.mgh.harvard.edu/fswiki/DownloadAndInstall) | Linux-centos6_x86_64-stable-pub-v6.0.0-2beb96c |
| [MATLAB](https://www.mathworks.com/products/matlab.html) | R2023a |
| Python | 3.8.10 or 3.10 |
| [ROCKETSHIP](../integration/rocketship.md) + parametric_scripts | 1.2 |
| [HD-BET](https://github.com/MIC-DKFZ/HD-BET) | latest |

!!! warning "FreeSurfer version"
    The specific FreeSurfer build listed above is required for white matter parcellation (`-f` flag). Other versions may work but are untested.

---

## Next Steps

- [Set up your BIDS data](bids-setup.md)
- [Process Data guide](process-data.md)
