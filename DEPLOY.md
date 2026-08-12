# PyPI Deployment Guide for Pyxelator

## Releasing (automated)

`.github/workflows/publish.yml` builds and uploads on a tag. It does not run on
a plain push to main, on purpose: a PyPI version can never be replaced, so every
upload has to be deliberate.

```bash
# 1. Bump the version in pyproject.toml, setup.py and pyxelator/__init__.py
# 2. Update the changelog in README.md
# 3. Commit, then tag
git tag v0.5.0
git push origin main
git push origin v0.5.0
```

The workflow runs the tests, checks the tag matches the version in
pyproject.toml, builds, runs `twine check`, then waits for approval on the
`pypi` environment before uploading.

To rehearse against TestPyPI, run the workflow manually from the Actions tab
with target `testpypi`.

### One-time setup

Uploads use PyPI Trusted Publishing, so there is no API token stored anywhere.

1. On PyPI, go to the project, then Publishing, then add a GitHub publisher:
   - Owner: `idejongkok`
   - Repository: `pyxelator`
   - Workflow: `publish.yml`
   - Environment: `pypi`
2. Repeat on test.pypi.org with environment `testpypi`.
3. In GitHub, Settings then Environments, create `pypi` and add yourself as a
   required reviewer. That is the gate that stops an accidental tag shipping.

Actions are pinned to commit SHAs rather than tags, since a tag can be moved to
point at different code. The version each SHA corresponds to is in the trailing
comment, and Dependabot opens a monthly PR when one moves. Do not replace a pin
with a tag when updating by hand.

---

## Releasing (manual)

Only needed if the workflow is unavailable.

## Prerequisites

Install required tools:
```bash
pip install --upgrade pip
pip install build twine
```

## Step 1: Test the Package Locally

Build the package:
```bash
python -m build
```

This will create:
- `dist/pyxelator-0.1.0.tar.gz` (source distribution)
- `dist/pyxelator-0.1.0-py3-none-any.whl` (wheel distribution)

## Step 2: Test Installation Locally

```bash
pip install dist/pyxelator-0.1.0-py3-none-any.whl
```

Test it works:
```python
from pyxelator import find, click, fill
print("Pyxelator imported successfully!")
```

## Step 3: Upload to TestPyPI (Optional but Recommended)

Register at https://test.pypi.org/account/register/

Upload to TestPyPI:
```bash
python -m twine upload --repository testpypi dist/*
```

Test installation from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ pyxelator
```

## Step 4: Upload to PyPI

Register at https://pypi.org/account/register/

Upload to PyPI:
```bash
python -m twine upload dist/*
```

You'll be prompted for:
- Username: your PyPI username
- Password: your PyPI password or token

## Step 5: Verify Installation

```bash
pip install pyxelator
```

## Using API Token (Recommended)

1. Go to https://pypi.org/manage/account/token/
2. Create a new API token
3. Use token for upload:

```bash
python -m twine upload -u __token__ -p pypi-YOUR_TOKEN_HERE dist/*
```

## Publishing Updates

When releasing a new version:

1. Update version in:
   - `pyxelator/__init__.py` (__version__)
   - `setup.py` (version)
   - `pyproject.toml` (version)

2. Rebuild and upload:
```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build new version
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

## Checklist Before Publishing

- [ ] All tests passing (`pytest -v`)
- [ ] README.md is complete and accurate
- [ ] Version numbers updated in all files
- [ ] LICENSE file included
- [ ] requirements.txt is accurate
- [ ] Tested package installation locally
- [ ] GitHub repository created (optional)

## Common Issues

**Issue: Package name already taken**
Solution: Choose a different name in setup.py and pyproject.toml

**Issue: Invalid credentials**
Solution: Use API token instead of password

**Issue: Missing files in distribution**
Solution: Check MANIFEST.in includes all necessary files
