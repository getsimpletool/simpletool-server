#!/bin/bash
# Script to clean up temporary files created by build_package.sh

echo "=== Cleaning up build artifacts ==="

# Remove build directories
echo "Removing build directories..."
rm -rf build/
rm -rf dist/
rm -rf .eggs/
rm -rf *.egg-info/
rm -rf mcpo_simple_server.egg-info/
rm -rf mcpo_simple_server/__pycache__/



# Remove any temporary files that might be created during the build process
echo "Removing temporary files..."
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name ".pytest_cache" -type d -exec rm -rf {} +
find . -name ".coverage" -delete
find . -name "htmlcov" -type d -exec rm -rf {} +

# Remove any .DS_Store files (for macOS users)
find . -name ".DS_Store" -delete

echo "=== Cleanup complete ==="
echo "All build artifacts and temporary files have been removed."
