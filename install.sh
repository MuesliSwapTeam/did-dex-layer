#!/bin/bash
# Complete installation script for DID DEX Layer project

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "==================================="
echo "DID DEX Layer - Installation Script"
echo "==================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python version: $PYTHON_VERSION"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "⚠️  WARNING: You are not in a virtual environment!"
    echo "It's recommended to use a virtual environment."
    echo ""
    read -p "Create a virtual environment now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo "✓ Virtual environment created"
        echo ""
        echo "Please activate it and re-run this script:"
        echo "  source venv/bin/activate"
        echo "  ./install.sh"
        exit 0
    fi
fi

# Step 1: Check for PyCardano wheel
echo ""
echo "Step 1: Checking PyCardano dependency..."
PYCARDANO_WHEEL=$(find vendor -name "pycardano-*.whl" 2>/dev/null | head -n 1)

if [ -z "$PYCARDANO_WHEEL" ]; then
    echo "⚠️  PyCardano wheel not found in vendor/"
    echo ""
    echo "Options:"
    echo "  1. Place pycardano wheel in vendor/ directory (recommended)"
    echo "  2. Use public PyCardano from PyPI (may have limited features)"
    echo ""
    read -p "Use public PyCardano? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing public PyCardano..."
        pip install "pycardano>=0.8.0"
        echo "✓ Public PyCardano installed (some features may be unavailable)"
    else
        echo ""
        echo "❌ Installation cancelled."
        echo "Please obtain the pycardano wheel and place it in vendor/"
        echo "Then re-run this script."
        exit 1
    fi
else
    echo "✓ Found PyCardano wheel: $(basename "$PYCARDANO_WHEEL")"
    echo ""
    echo "Installing PyCardano from wheel..."
    pip install "$PYCARDANO_WHEEL" --force-reinstall
    echo "✓ PyCardano installed"
fi

# Step 2: Install other dependencies
echo ""
echo "Step 2: Installing other dependencies from requirements.txt..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Step 3: Verify installation
echo ""
echo "Step 3: Verifying installation..."
python3 -c "import pycardano; print(f'✓ PyCardano version: {pycardano.__version__}')" 2>/dev/null || echo "⚠️  PyCardano import failed"
python3 -c "import opshin; print('✓ OpShin import successful')" 2>/dev/null || echo "⚠️  OpShin import failed"
python3 -c "import flask; print('✓ Flask import successful')" 2>/dev/null || echo "⚠️  Flask import failed"

echo ""
echo "==================================="
echo "Installation Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  - Review README.md for usage instructions"
echo "  - Configure Ogmios connection (see README.md)"
echo "  - Run tests: pytest src/tests/"
echo "  - Check TEST_USER_GUIDE.md for testing guide"
echo ""

