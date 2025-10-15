# Vendor Directory

This directory contains vendored dependencies that are not available on PyPI or require specific versions.

## PyCardano

This directory includes a pre-built wheel of PyCardano with project-specific patches.

**Included:** `pycardano-0.9.0-py3-none-any.whl`

### Installation

The wheel is included in the repository for convenience. 

For complete installation instructions, see the **Installation** section in [README.md](../README.md).

Quick install:
```bash
./install.sh
```

### Updating the Wheel

If you need to update the PyCardano wheel:

1. Clone the source repository:
   ```bash
   cd /tmp
   git clone https://github.com/MuesliSwapLabs/pycardano.git
   cd pycardano
   git checkout 5d9da9d865c59e71fdc71e51aff7cc362abe3d32
   ```

2. Build the wheel:
   ```bash
   python3 -m venv build_env
   source build_env/bin/activate
   pip install build
   python -m build --wheel
   ```

3. Copy the new wheel:
   ```bash
   cp dist/*.whl /path/to/did-dex-layer/vendor/
   ```

### Wheel Details

- **Version:** 0.9.0
- **Type:** Pure Python (py3-none-any)
- **Compatibility:** Works on all platforms with Python 3.7+
- **Source:** Based on commit 5d9da9d865c59e71fdc71e51aff7cc362abe3d32

