#!/usr/bin/env bash
# Script to test and build the mcpo-simple-server package

set -euo pipefail  # Exit on error, undefined vars fail, pipefail

echo "=== Testing package imports ===="
cd "$(dirname "$0")"
# Uncomment when you have tests
# python tests/test_imports.py

echo "=== Cleaning previous builds ==="
rm -rf build/ dist/ *.egg-info/

echo "=== Building package ==="
python -m pip install --upgrade pip
python -m pip install build twine
python -m build

echo "=== Package build complete ===="
echo "Distribution files:"
ls -l dist/
echo ""

echo "=== ======================= ==="
echo "To install locally for testing:"
echo "pip install dist/*.whl"
echo ""
echo "To publish to TestPyPI:"
echo "python -m twine upload --repository testpypi dist/*"
echo ""
echo "To publish to PyPI:"
echo "python -m twine upload dist/*"

echo "=== WE ARE DONE! WHAT NEXT? ==="

# Ask user if they want to install locally
read -r -p "Install mcpo-simple-server locally for testing? [y/N]: " install_locally
case "$install_locally" in
  [Yy]*)
    echo "Removing any existing mcpo-simple-server package..."
    pip uninstall -y mcpo-simple-server || true
    echo "Installing mcpo-simple-server package locally..."
    pip install --force-reinstall dist/*.whl
    pip show mcpo-simple-server
    ;;
  *) ;;
esac

# Ask user if they want to publish to TestPyPI
read -r -p "Publish to TestPyPI? [y/N]: " publish_test
case "$publish_test" in
  [Yy]*)
    echo "Publishing mcpo-simple-server package to TestPyPI..."
    python -m twine upload --repository testpypi dist/*
    ;;
  *) ;;
esac

# Ask user if they want to publish to PyPI
read -r -p "Publish to PyPI? [y/N]: " publish_pypi
case "$publish_pypi" in
  [Yy]*)
    echo "Publishing mcpo-simple-server package to PyPI..."
    python -m twine upload dist/*
    ;;
  *) ;;
esac

echo "Build script completed."
