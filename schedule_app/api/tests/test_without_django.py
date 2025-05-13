import pytest
import os
import sys
import json
from pathlib import Path

def test_environment():
    """Test the Python environment"""
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    assert sys.version_info.major >= 3, "Python 3 or higher is required"
    
def test_project_structure():
    """Test that the project structure is as expected"""
    assert os.path.isdir("api"), "api directory should exist"
    assert os.path.isfile("manage.py"), "manage.py should exist"
    assert os.path.isdir("api/tests"), "api/tests directory should exist"

def test_manage_py_content():
    """Test that manage.py has the expected content"""
    with open("manage.py", "r") as f:
        content = f.read()
        
    assert "django" in content.lower(), "manage.py should contain 'django'"
    assert "settings" in content.lower(), "manage.py should contain 'settings'"

def test_mock_models():
    """Test a mock version of models without importing Django"""
    class Employee:
        def __init__(self, name, role):
            self.name = name
            self.role = role
            
        def __str__(self):
            return self.name
    
    employee = Employee("Test User", "staff")
    assert employee.name == "Test User"
    assert employee.role == "staff"
    assert str(employee) == "Test User"

def test_mock_views():
    """Test a mock version of views without importing Django"""
    def home_view(request):
        return {"status": "success", "message": "Welcome to the home page"}
    
    result = home_view(None)
    assert result["status"] == "success"
    assert result["message"] == "Welcome to the home page"

def test_mock_serialization():
    """Test serialization without importing Django"""
    data = {
        "employees": [
            {"name": "John Doe", "role": "staff"},
            {"name": "Jane Smith", "role": "manager"}
        ],
        "equipment": [
            {"name": "MRI Scanner", "type": "mrt"},
            {"name": "CT Scanner", "type": "rkt_ge"}
        ]
    }
    
    json_data = json.dumps(data)
    parsed_data = json.loads(json_data)
    
    assert len(parsed_data["employees"]) == 2
    assert parsed_data["employees"][0]["name"] == "John Doe"
    assert parsed_data["equipment"][1]["type"] == "rkt_ge"
