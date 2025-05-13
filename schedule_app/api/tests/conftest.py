import os
import pytest

@pytest.fixture
def sample_employee():
    """Fixture that returns a sample employee dictionary"""
    return {
        "id": 1,
        "full_name": "Test Employee",
        "email": "test@example.com",
        "role": "staff",
        "position": "Doctor",
        "rate": 1.5
    }

@pytest.fixture
def sample_equipment():
    """Fixture that returns a sample equipment dictionary"""
    return {
        "id": 1,
        "name": "Test Equipment",
        "equipment_type": "mrt",
        "shift_morning": True,
        "shift_evening": True,
        "shift_night": False
    }

@pytest.fixture
def sample_schedule():
    """Fixture that returns a sample schedule dictionary"""
    return {
        "id": 1,
        "employee_id": 1,
        "equipment_id": 1,
        "shift_type": "morning",
        "date": "2023-05-01"
    }

@pytest.fixture
def sample_time_off_request():
    """Fixture that returns a sample time off request dictionary"""
    return {
        "id": 1,
        "employee_id": 1,
        "start_date": "2023-05-01",
        "end_date": "2023-05-07",
        "reason": "Vacation",
        "priority": "medium",
        "status": "pending"
    }

@pytest.fixture
def mock_db():
    """Mock database with sample data"""
    return {
        "employees": [
            {
                "id": 1,
                "full_name": "Test Employee",
                "email": "test@example.com",
                "role": "staff"
            },
            {
                "id": 2,
                "full_name": "Test Manager",
                "email": "manager@example.com",
                "role": "manager"
            }
        ],
        "equipment": [
            {
                "id": 1,
                "name": "MRI Scanner",
                "equipment_type": "mrt"
            },
            {
                "id": 2,
                "name": "CT Scanner",
                "equipment_type": "rkt_ge"
            }
        ]
    } 