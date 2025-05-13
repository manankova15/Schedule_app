import pytest
import os
import sys

def test_django_settings():
    """Test that Django settings can be imported correctly"""
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
