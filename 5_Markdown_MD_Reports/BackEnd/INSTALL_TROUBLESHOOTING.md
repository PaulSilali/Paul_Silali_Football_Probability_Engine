# Installation Troubleshooting Guide

## Issue: NumPy Build Error on Windows

If you encounter errors like:
```
ERROR: Unknown compiler(s): [['icl'], ['cl'], ['cc'], ['gcc'], ['clang'], ['clang-cl'], ['pgcc']]
```

This means NumPy is trying to build from source but no C compiler is available.

## Solutions

### Option 1: Install NumPy Separately First (Recommended)

Install NumPy with a version that has pre-built wheels:

```bash
pip install numpy
pip install -r requirements.txt
```

This will install the latest NumPy with pre-built wheels, then install other packages.

### Option 2: Use Python 3.11 or 3.12

Python 3.14 is very new and some packages may not have pre-built wheels yet. Consider using Python 3.11 or 3.12:

```bash
# Check your Python version
python --version

# If you have Python 3.11 or 3.12 available, use that instead
py -3.11 -m venv venv
# or
py -3.12 -m venv venv
```

### Option 3: Install Visual Studio Build Tools

If you need to build from source, install Microsoft Visual Studio Build Tools:

1. Download from: https://visualstudio.microsoft.com/downloads/
2. Install "Desktop development with C++" workload
3. Restart your terminal
4. Try installing again

### Option 4: Install Packages One by One

If bulk installation fails, install critical packages first:

```bash
pip install numpy scipy pandas
pip install -r requirements.txt
```

## Quick Fix Command

Try this sequence:

```bash
# Upgrade pip first
pip install --upgrade pip

# Install NumPy separately (will get latest with wheels)
pip install numpy

# Then install everything else
pip install -r requirements.txt
```

## Verify Installation

After installation, verify:

```bash
python -c "import numpy; print(numpy.__version__)"
python -c "import fastapi; print('FastAPI installed')"
```

