# PyPI Deployment Guide for Pyxelator

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
