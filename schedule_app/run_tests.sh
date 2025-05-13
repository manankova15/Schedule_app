#!/bin/bash

CURRENT_DIR=$(pwd)
BACKEND_DIR="${CURRENT_DIR}"

echo "Current directory: ${CURRENT_DIR}"
echo "Backend directory: ${BACKEND_DIR}"

if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "Installing required packages..."
    pip install pytest pytest-django pytest-cov django djangorestframework
    pip install djangorestframework-simplejwt django-cors-headers
    pip install selenium chromedriver-py pytest-xdist pytest-pythonpath
fi

export DJANGO_SETTINGS_MODULE=backend.hospital.settings
export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH}"
echo "Set DJANGO_SETTINGS_MODULE to ${DJANGO_SETTINGS_MODULE}"
echo "Set PYTHONPATH to ${PYTHONPATH}"

mkdir -p api/tests
touch api/tests/__init__.py

cat > api/tests/test_settings.py << 'EOL'
import pytest
import os
import sys

def test_django_settings():
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    
    try:
        from django.conf import settings
        print(f"Django settings module: {settings.SETTINGS_MODULE}")
        assert hasattr(settings, 'INSTALLED_APPS')
        print("Django settings loaded successfully!")
    except ImportError as e:
        pytest.fail(f"Failed to import Django settings: {e}")
    except Exception as e:
        pytest.fail(f"Error accessing Django settings: {e}")
EOL

echo "Running tests with coverage..."
cd "${BACKEND_DIR}" && python -m pytest api/tests/test_settings.py -v

TEST_EXIT_CODE=$?
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo "Tests failed! See console output above for errors."
    exit $TEST_EXIT_CODE
fi

echo ""
echo "Test Results Summary:"
echo "====================="
echo "Basic settings test passed. Now you can run more comprehensive tests."

exit $TEST_EXIT_CODE 