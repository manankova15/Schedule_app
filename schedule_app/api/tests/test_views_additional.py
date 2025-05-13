import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client
from api.models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill,
    TimeOffRequest
)
import datetime

User = get_user_model()

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def setup_data():
    manager_user = User.objects.create_user(
        email='manager@example.com',
        password='manager123'
    )
    
    staff_user = User.objects.create_user(
        email='staff@example.com',
        password='staff123'
    )
    
    manager = Employee.objects.create(
        user=manager_user,
        full_name='Test Manager',
        email='manager@example.com',
        role='manager'
    )
    
    staff = Employee.objects.create(
        user=staff_user,
        full_name='Test Staff',
        email='staff@example.com',
        role='staff'
    )
    
    equipment = Equipment.objects.create(
        name='Test Equipment',
        equipment_type='mrt',
        shift_morning=True,
        shift_evening=True,
        shift_night=False
    )
    
    EmployeeEquipmentSkill.objects.create(
        employee=staff,
        equipment=equipment,
        skill_level='primary'
    )
    
    today = datetime.date.today()
    
    time_off = TimeOffRequest.objects.create(
        employee=staff,
        start_date=today,
        end_date=today + datetime.timedelta(days=3),
        reason='Test Vacation',
        priority='medium',
        status='pending'
    )
    
    return {
        'manager_user': manager_user,
        'staff_user': staff_user,
        'manager': manager,
        'staff': staff,
        'equipment': equipment,
        'time_off': time_off
    }

@pytest.mark.django_db
class TestManagerViews:
    def test_manage_equipment_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        url = reverse('manage_equipment')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'equipment_list' in response.context
        assert setup_data['equipment'] in response.context['equipment_list']
    
    def test_add_equipment_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        url = reverse('add_equipment')
        response = client.get(url)
        
        assert response.status_code == 200
        
        data = {
            'name': 'New Equipment',
            'equipment_type': 'rkt_ge',
            'shift_morning': 'on',
            'shift_evening': 'on',
            'shift_night': 'on'
        }
        
        response = client.post(url, data)
        assert response.status_code == 302
        
        assert Equipment.objects.filter(name='New Equipment').exists()
    
    def test_manage_employees_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        url = reverse('manage_employees')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'employees' in response.context
        assert setup_data['staff'] in response.context['employees']
    
    def test_employee_detail_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        url = reverse('employee_detail', args=[setup_data['staff'].id])
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'employee' in response.context
        assert response.context['employee'] == setup_data['staff']

@pytest.mark.django_db
class TestEquipmentViews:
    def test_edit_equipment_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        url = reverse('edit_equipment', args=[setup_data['equipment'].id])
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'equipment' in response.context
        assert response.context['equipment'] == setup_data['equipment']
        
        data = {
            'name': 'Updated Equipment',
            'equipment_type': 'rkt_ge',
            'shift_morning': 'on',
            'shift_evening': '',
            'shift_night': ''
        }
        
        response = client.post(url, data)
        assert response.status_code == 302
        
        setup_data['equipment'].refresh_from_db()
        assert setup_data['equipment'].name == 'Updated Equipment'
        assert setup_data['equipment'].shift_morning is True
        assert setup_data['equipment'].shift_evening is False
    
    def test_delete_equipment_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        equipment_to_delete = Equipment.objects.create(
            name='Equipment To Delete',
            equipment_type='mrt'
        )
        
        url = reverse('delete_equipment', args=[equipment_to_delete.id])
        response = client.post(url)
        
        assert response.status_code == 302
        
        assert not Equipment.objects.filter(id=equipment_to_delete.id).exists()

@pytest.mark.django_db
class TestTimeOffRequestViews:
    def test_approve_request_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        url = reverse('approve_request', args=[setup_data['time_off'].id])
        response = client.get(url)
        
        assert response.status_code == 302
        
        setup_data['time_off'].refresh_from_db()
        assert setup_data['time_off'].status == 'approved'
    
    def test_reject_request_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        today = datetime.date.today()
        
        time_off_to_reject = TimeOffRequest.objects.create(
            employee=setup_data['staff'],
            start_date=today + datetime.timedelta(days=5),
            end_date=today + datetime.timedelta(days=8),
            reason='Another Vacation',
            priority='low',
            status='pending'
        )
        
        url = reverse('reject_request', args=[time_off_to_reject.id])
        response = client.get(url)
        
        assert response.status_code == 200
        
        data = {
            'manager_comment': 'Rejected due to high workload'
        }
        
        response = client.post(url, data)
        assert response.status_code == 302

        time_off_to_reject.refresh_from_db()
        assert time_off_to_reject.status == 'rejected'
        assert time_off_to_reject.manager_comment == 'Rejected due to high workload'

@pytest.mark.django_db
class TestEmployeeViews:
    def test_add_skills_view(self, client, setup_data):
        client.force_login(setup_data['manager_user'])
        
        url = reverse('manage_skills', args=[setup_data['staff'].id])
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'employee' in response.context
        assert response.context['employee'] == setup_data['staff']
        
        new_equipment = Equipment.objects.create(
            name='New Equipment For Skill',
            equipment_type='rkt_toshiba'
        )
        
        data = {
            f'skill_{new_equipment.id}': 'secondary'
        }
        
        response = client.post(url, data)
        assert response.status_code == 302
        
        assert EmployeeEquipmentSkill.objects.filter(
            employee=setup_data['staff'],
            equipment=new_equipment,
            skill_level='secondary'
        ).exists() 