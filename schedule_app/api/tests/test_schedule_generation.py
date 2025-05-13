import pytest
from django.contrib.auth import get_user_model
from api.models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill,
    TimeOffRequest
)
from datetime import datetime, timedelta, date
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from api.views import ScheduleViewSet

User = get_user_model()

@pytest.fixture
def setup_schedule_data():
    user1 = User.objects.create_user(
        email='employee1@example.com',
        password='password123'
    )
    
    user2 = User.objects.create_user(
        email='employee2@example.com',
        password='password123'
    )
    
    manager_user = User.objects.create_user(
        email='manager@example.com',
        password='password123'
    )
    
    employee1 = Employee.objects.create(
        user=user1,
        full_name='Employee One',
        email='employee1@example.com',
        role='staff',
        rate=1,
        shift_availability='all_shifts'
    )
    
    employee2 = Employee.objects.create(
        user=user2,
        full_name='Employee Two',
        email='employee2@example.com',
        role='staff',
        rate=1.5,
        shift_availability='morning_only'
    )
    
    manager = Employee.objects.create(
        user=manager_user,
        full_name='Manager',
        email='manager@example.com',
        role='manager',
        rate=1,
        shift_availability='all_shifts'
    )
    
    mri = Equipment.objects.create(
        name='MRI Scanner',
        equipment_type='mrt',
        shift_morning=True,
        shift_evening=True,
        shift_night=False
    )
    
    ct = Equipment.objects.create(
        name='CT Scanner',
        equipment_type='rkt_ge',
        shift_morning=True,
        shift_evening=True,
        shift_night=True
    )
    
    EmployeeEquipmentSkill.objects.create(
        employee=employee1,
        equipment=mri,
        skill_level='primary'
    )
    
    EmployeeEquipmentSkill.objects.create(
        employee=employee1,
        equipment=ct,
        skill_level='secondary'
    )
    
    EmployeeEquipmentSkill.objects.create(
        employee=employee2,
        equipment=ct,
        skill_level='primary'
    )
    
    EmployeeEquipmentSkill.objects.create(
        employee=manager,
        equipment=mri,
        skill_level='primary'
    )
    
    return {
        'users': [user1, user2, manager_user],
        'employees': [employee1, employee2, manager],
        'equipment': [mri, ct]
    }

@pytest.mark.django_db
class TestScheduleGeneration:
    def test_get_available_employees(self, setup_schedule_data):
        data = setup_schedule_data
        today = date.today()
        
        schedule_viewset = ScheduleViewSet()
        
        available_employees = schedule_viewset._get_available_employees(
            employees=data['employees'],
            date=today,
            shift_type='morning',
            equipment=data['equipment'][0]
        )
        
        assert len(available_employees) >= 1
        assert data['employees'][0] in available_employees 
        assert data['employees'][2] in available_employees
        
        TimeOffRequest.objects.create(
            employee=data['employees'][0],
            start_date=today,
            end_date=today + timedelta(days=5),
            reason='Vacation',
            priority='medium',
            status='approved'
        )
        
        available_employees = schedule_viewset._get_available_employees(
            employees=data['employees'],
            date=today,
            shift_type='morning',
            equipment=data['equipment'][0]
        )
        
        assert data['employees'][0] not in available_employees
        assert data['employees'][2] in available_employees 
        
        available_employees = schedule_viewset._get_available_employees(
            employees=data['employees'],
            date=today,
            shift_type='night',
            equipment=data['equipment'][1]
        )
        
        assert data['employees'][1] not in available_employees
    
    def test_generate_schedule_api(self, setup_schedule_data):
        data = setup_schedule_data
        manager_user = data['users'][2]
        
        client = APIClient()
        client.force_authenticate(user=manager_user)
        
        today = date.today()
        next_week = today + timedelta(days=7)
        
        url = reverse('schedule-generate-schedule')
        request_data = {
            'start_date': today.strftime('%Y-%m-%d'),
            'end_date': next_week.strftime('%Y-%m-%d')
        }
        
        assert Schedule.objects.filter(
            date__gte=today,
            date__lte=next_week
        ).count() == 0
        
        response = client.post(url, request_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        assert Schedule.objects.filter(
            date__gte=today,
            date__lte=next_week
        ).exists()
        
        employee1_schedules = Schedule.objects.filter(employee=data['employees'][0])
        for schedule in employee1_schedules:
            assert schedule.equipment in data['equipment']
        
        employee2_schedules = Schedule.objects.filter(employee=data['employees'][1])
        for schedule in employee2_schedules:
            assert schedule.equipment == data['equipment'][1]
            assert schedule.shift_type == 'morning'
    
    def test_date_constraints(self, setup_schedule_data):
        data = setup_schedule_data
        employee1 = data['employees'][0]
        equipment1 = data['equipment'][0]
        today = date.today()
        
        if today.day == 1:
            test_date = today + timedelta(days=1)
        else:
            test_date = today
        
        Schedule.objects.create(
            employee=employee1,
            equipment=equipment1,
            shift_type='morning',
            date=test_date - timedelta(days=1)
        )
        
        schedule_viewset = ScheduleViewSet()
        available_employees = schedule_viewset._get_available_employees(
            employees=[employee1],
            date=test_date,
            shift_type='morning',
            equipment=equipment1
        )
        
        assert employee1 not in available_employees 