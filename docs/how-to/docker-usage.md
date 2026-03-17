# Using Docker

The DCEPrep Docker image bundles all required dependencies — FSL 6.0, ANTs 2.6.2, FreeSurfer 6.0, MATLAB, ROCKETSHIP, HD-BET, and the full Python environment — into a single container. No local software installation is needed beyond Docker itself.

---

## Image Tags

Images are available on Docker Hub for multiple MATLAB releases:

```
lsaca05/dce:<MATLAB_release>-<branch>
```

| Tag | MATLAB version | Branch |
|---|---|---|
| `R2023a-main` | R2023a | stable |
| `R2022a-main` | R2022a | stable |
| `R2021a-main` | R2021a | stable |
| `R2020a-main` | R2020a | stable |
| `R2023a-dev` | R2023a | development |

See [Docker Hub](https://hub.docker.com/repository/docker/lsaca05/dce/tags) for all available tags.

---

## Quick Launch with `run_docker.sh`

The recommended way to start the container:

1. **Edit `run_docker.sh` line 24** — set `DATA_DIR` to your data directory path
2. Run:

```bash
./run_docker.sh
```

The script mounts your data directory, license files, and the script preferences folder, then drops you into a shell inside the container at the DCEPrep working directory.

---

## What Gets Mounted

`run_docker.sh` mounts the following into the container:

| Host path | Container path | Purpose |
|---|---|---|
| Your data directory | `/data` (or configured path) | BIDS rawdata and derivatives |
| MATLAB license file | (MATLAB license path) | Enable MATLAB execution |
| FreeSurfer `license.txt` | `$FREESURFER_HOME/license.txt` | Enable FreeSurfer |
| `docker/files/` | `/opt/ROCKETSHIP/.../script_preferences.txt` | ROCKETSHIP preferences |
| `/etc/` | `/etc/` | System configuration |

---

## Pulling the Image Manually

```bash
docker pull lsaca05/dce:R2023a-main
```

---

## Running a Command Directly (Non-Interactive)

```bash
docker run --rm \
  -v /path/to/rawdata:/data/rawdata \
  -v /path/to/matlab.lic:/licenses/matlab.lic \
  -v /path/to/freesurfer/license.txt:/opt/freesurfer/license.txt \
  lsaca05/dce:R2023a-main \
  ./preprocess_all.sh -d /data/rawdata -b -Z
```

---

## GPU Support (iNESMA)

The Docker image supports CUDA 13. To use GPU acceleration for iNESMA smoothing:

```bash
docker run --gpus all --rm \
  -v /path/to/rawdata:/data/rawdata \
  lsaca05/dce:R2023a-main \
  ./DCE_all.sh -d /data/rawdata -S
```

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

---

## Building the Image Locally

```bash
docker build -t dce:local .
```

The Dockerfile performs a multi-stage build that installs CUDA 13, FSL, ANTs, FreeSurfer, and the Python environment. Build time is substantial (~30–60 minutes depending on hardware).

---

## Troubleshooting

!!! warning "Stub"
    Common Docker issues (license file not found, GPU not detected, permission errors on mounted volumes) and their solutions need to be documented here.
