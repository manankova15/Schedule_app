import pytest
import json

def test_employee_fixture(sample_employee):
    """Test the sample_employee fixture"""
    assert sample_employee["id"] == 1
    assert sample_employee["full_name"] == "Test Employee"
    assert sample_employee["role"] == "staff"
    assert sample_employee["rate"] == 1.5

def test_equipment_fixture(sample_equipment):
    """Test the sample_equipment fixture"""
    assert sample_equipment["id"] == 1
    assert sample_equipment["name"] == "Test Equipment"
    assert sample_equipment["equipment_type"] == "mrt"
    assert sample_equipment["shift_morning"] is True
    assert sample_equipment["shift_evening"] is True
    assert sample_equipment["shift_night"] is False

def test_schedule_fixture(sample_schedule):
    """Test the sample_schedule fixture"""
    assert sample_schedule["id"] == 1
    assert sample_schedule["employee_id"] == 1
    assert sample_schedule["equipment_id"] == 1
    assert sample_schedule["shift_type"] == "morning"
    assert sample_schedule["date"] == "2023-05-01"

def test_time_off_request_fixture(sample_time_off_request):
    """Test the sample_time_off_request fixture"""
    assert sample_time_off_request["id"] == 1
    assert sample_time_off_request["employee_id"] == 1
    assert sample_time_off_request["start_date"] == "2023-05-01"
    assert sample_time_off_request["end_date"] == "2023-05-07"
    assert sample_time_off_request["reason"] == "Vacation"
    assert sample_time_off_request["priority"] == "medium"
    assert sample_time_off_request["status"] == "pending"

def test_mock_db(mock_db):
    """Test the mock_db fixture"""
    assert len(mock_db["employees"]) == 2
    assert mock_db["employees"][0]["full_name"] == "Test Employee"
    assert mock_db["employees"][1]["role"] == "manager"
    
    assert len(mock_db["equipment"]) == 2
    assert mock_db["equipment"][0]["name"] == "MRI Scanner"
    assert mock_db["equipment"][1]["equipment_type"] == "rkt_ge"
    
    json_data = json.dumps(mock_db)
    parsed_data = json.loads(json_data)
    assert parsed_data == mock_db

def test_mock_employee_search(mock_db):
    """Test searching for an employee in the mock database"""
    def find_employee_by_id(employee_id):
        for employee in mock_db["employees"]:
            if employee["id"] == employee_id:
                return employee
        return None
    
    employee1 = find_employee_by_id(1)
    assert employee1 is not None
    assert employee1["full_name"] == "Test Employee"
    
    employee2 = find_employee_by_id(2)
    assert employee2 is not None
    assert employee2["full_name"] == "Test Manager"
    
    employee3 = find_employee_by_id(3)
    assert employee3 is None

def test_mock_schedule_generation(mock_db, sample_schedule):
    """Test mock schedule generation"""
    def generate_schedule(employee_id, equipment_id, date, shift_type):
        return {
            "id": len(mock_db.get("schedules", [])) + 1,
            "employee_id": employee_id,
            "equipment_id": equipment_id,
            "date": date,
            "shift_type": shift_type
        }
    
    if "schedules" not in mock_db:
        mock_db["schedules"] = []
    
    schedule = generate_schedule(1, 1, "2023-05-01", "morning")
    mock_db["schedules"].append(schedule)
    
    assert len(mock_db["schedules"]) == 1
    assert mock_db["schedules"][0]["employee_id"] == 1
    assert mock_db["schedules"][0]["shift_type"] == "morning" 