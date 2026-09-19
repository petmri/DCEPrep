# Contributing

---

## Reporting Issues

Please open an issue on [GitHub](https://github.com/petmri/DCEPrep/issues) to report bugs or request features. Include:

- The command you ran
- Relevant log output (`logs/preprocessing_log_*.txt` or `logs/dce_log_*.txt`)
- Your environment (Docker tag or local install details)

---

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable releases — Docker images tagged with `-main` are built from this branch |
| `dev` | Active development — new features and fixes land here first |
| Feature branches | Short-lived branches for individual features or fixes, branched from `dev` |

To contribute:

1. Fork the repository
2. Create a feature branch from `dev`
3. Make your changes and push to your fork
4. Open a pull request targeting `dev`

---

## Development Setup

### Local environment

```bash
# Clone the repository
git clone https://github.com/petmri/DCEPrep.git
cd DCEPrep
git checkout dev

# Set up Python environment
python3 -m venv tf
source tf/bin/activate
pip install -r venv_requirements.txt
```

You will also need FSL, ANTs, FreeSurfer, and MATLAB installed locally (see [Installation](../getting-started/installation.md)).

### Running with Docker

For testing without a full local install, use the dev Docker image:

```bash
docker pull lsaca05/dce:R2023a-dev
```

### CI/CD

The GitHub Actions workflow automatically clones the `petmri/ROCKETSHIP` dev branch and builds the Docker image. Check `.github/workflows/` for the current CI configuration.

---

## Building Docs Locally

The site is built with [Zensical](https://zensical.org/), the successor to
Material for MkDocs. It reads the same `mkdocs.yml`.

```bash
pip install -r requirements-docs.txt
zensical serve
```

Then open `http://127.0.0.1:8000` in a browser.
