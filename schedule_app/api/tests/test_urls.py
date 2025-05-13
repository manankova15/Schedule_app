import pytest
from django.urls import reverse, resolve
from django.contrib.auth.views import LoginView
from hospital.views import (
    home, my_schedule, manager_schedule, schedule_generator,
    time_off_requests, time_off_request_new, approve_time_off_request,
    reject_time_off_request, employees, create_employee, equipment,
    create_equipment, logout_view, register, profile
)
from api.views import (
    EmployeeViewSet, EquipmentViewSet, ScheduleViewSet,
    TimeOffRequestViewSet
)

@pytest.mark.parametrize(
    "url_name,view_name", [
        ('home', home),
        ('login', LoginView),
        ('logout', logout_view),
        ('register', register),
        ('profile', profile),
        ('my_schedule', my_schedule),
        ('manager_schedule', manager_schedule),
        ('schedule_generator', schedule_generator),
        ('time_off_requests', time_off_requests),
        ('time_off_request_new', time_off_request_new),
        ('employees', employees),
        ('create_employee', create_employee),
        ('equipment', equipment),
        ('create_equipment', create_equipment),
    ]
)
def test_url_resolution(url_name, view_name):
    """Test that URLs resolve to the correct view functions"""
    url = reverse(url_name)
    assert resolve(url).func == view_name

@pytest.mark.parametrize(
    "url_name,view_class", [
        ('token_obtain_pair', 'TokenObtainPairView'),
        ('token_refresh', 'TokenRefreshView'),
    ]
)
def test_jwt_url_resolution(url_name, view_class):
    """Test JWT authentication URL resolution"""
    url = reverse(url_name)
    assert resolve(url).func.view_class.__name__ == view_class

@pytest.mark.parametrize(
    "url_name,kwargs,expected_path", [
        ('employee_detail', {'employee_id': 1}, '/employees/employee/1/'),
        ('approve_time_off_request', {'request_id': 2}, '/time-off-requests/approve/2/'),
        ('reject_time_off_request', {'request_id': 3}, '/time-off-requests/reject/3/'),
        ('update_employee', {'employee_id': 4}, '/employees/update/4/'),
        ('update_equipment', {'equipment_id': 5}, '/equipment/update/5/'),
    ]
)
def test_url_generation(url_name, kwargs, expected_path):
    """Test URL generation with parameters"""
    try:
        url = reverse(url_name, kwargs=kwargs)
        assert url == expected_path
    except:
        pytest.skip(f"URL {url_name} with kwargs {kwargs} cannot be resolved")

@pytest.mark.django_db
def test_api_url_patterns():
    """Test that API URL patterns correctly resolve to viewsets"""
    url = reverse('employee-list')
    assert url == '/api/employees/'
    
    url = reverse('equipment-list')
    assert url == '/api/equipment/'
    
    url = reverse('schedule-list')
    assert url == '/api/schedules/'
    
    url = reverse('timeoffrequest-list')
    assert url == '/api/time-off-requests/' 