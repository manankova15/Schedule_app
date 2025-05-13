import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client
from api.models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill,
    TimeOffRequest, CustomUser
)
from django.utils import timezone

User = get_user_model()

@pytest.fixture
def admin_client():
    admin_user = User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123'
    )
    
    client = Client()
    client.force_login(admin_user)
    return client

@pytest.fixture
def admin_user():
    """Create an admin user for testing admin interface"""
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )
    return admin

@pytest.mark.django_db
class TestAdminSite:
    def test_customuser_admin(self, admin_client):
        url = reverse('admin:api_customuser_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        url = reverse('admin:api_customuser_add')
        response = admin_client.get(url)
        assert response.status_code == 200
        
    def test_employee_admin(self, admin_client):
        url = reverse('admin:api_employee_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        url = reverse('admin:api_employee_add')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        user = User.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            role='staff'
        )
        
        url = reverse('admin:api_employee_change', args=[employee.id])
        response = admin_client.get(url)
        assert response.status_code == 200
        
    def test_equipment_admin(self, admin_client):
        url = reverse('admin:api_equipment_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        url = reverse('admin:api_equipment_add')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        equipment = Equipment.objects.create(
            name='Test Equipment',
            equipment_type='mrt'
        )
        
        url = reverse('admin:api_equipment_change', args=[equipment.id])
        response = admin_client.get(url)
        assert response.status_code == 200
        
    def test_schedule_admin(self, admin_client):
        url = reverse('admin:api_schedule_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        user = User.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            role='staff'
        )
        
        equipment = Equipment.objects.create(
            name='Test Equipment',
            equipment_type='mrt'
        )
        
        from datetime import date
        schedule = Schedule.objects.create(
            employee=employee,
            equipment=equipment,
            shift_type='morning',
            date=date.today()
        )
        
        url = reverse('admin:api_schedule_change', args=[schedule.id])
        response = admin_client.get(url)
        assert response.status_code == 200
        
    def test_employeeequipmentskill_admin(self, admin_client):
        url = reverse('admin:api_employeeequipmentskill_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        user = User.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            role='staff'
        )
        
        equipment = Equipment.objects.create(
            name='Test Equipment',
            equipment_type='mrt'
        )
        
        skill = EmployeeEquipmentSkill.objects.create(
            employee=employee,
            equipment=equipment,
            skill_level='primary'
        )
        
        url = reverse('admin:api_employeeequipmentskill_change', args=[skill.id])
        response = admin_client.get(url)
        assert response.status_code == 200
        
    def test_timeoffrequest_admin(self, admin_client):
        url = reverse('admin:api_timeoffrequest_changelist')
        response = admin_client.get(url)
        assert response.status_code == 200
        
        user = User.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            role='staff'
        )
        
        from datetime import date, timedelta
        today = date.today()
        time_off = TimeOffRequest.objects.create(
            employee=employee,
            start_date=today,
            end_date=today + timedelta(days=5),
            reason='Vacation',
            priority='medium',
            status='pending'
        )
        
        url = reverse('admin:api_timeoffrequest_change', args=[time_off.id])
        response = admin_client.get(url)
        assert response.status_code == 200

@pytest.mark.django_db
class TestAdminInterface:
    def test_admin_login(self, client, admin_user):
        """Test admin login functionality"""
        url = reverse('admin:login')
        response = client.get(url)
        assert response.status_code == 200
        
        response = client.post(url, {
            'username': 'admin',
            'password': 'adminpass123',
            'next': reverse('admin:index')
        })
        
        assert response.status_code == 302
        assert response.url == reverse('admin:index')
    
    def test_admin_index(self, client, admin_user):
        """Test admin index page"""
        client.force_login(admin_user)
        url = reverse('admin:index')
        response = client.get(url)
        
        assert response.status_code == 200
        assert b'Site administration' in response.content
    
    def test_custom_user_admin(self, client, admin_user):
        """Test CustomUser admin interface"""
        client.force_login(admin_user)
        
        test_user = CustomUser.objects.create_user(
            email='testuser@example.com',
            password='password123'
        )
        
        url = reverse('admin:api_customuser_changelist')
        response = client.get(url)
        assert response.status_code == 200
        assert b'testuser@example.com' in response.content
        
        url = reverse('admin:api_customuser_change', args=[test_user.id])
        response = client.get(url)
        assert response.status_code == 200
        assert b'testuser@example.com' in response.content
        
        url = reverse('admin:api_customuser_add')
        response = client.get(url)
        assert response.status_code == 200
    
    def test_employee_admin(self, client, admin_user):
        """Test Employee admin interface"""
        client.force_login(admin_user)
        
        user = CustomUser.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            role='staff'
        )
        
        url = reverse('admin:api_employee_changelist')
        response = client.get(url)
        assert response.status_code == 200
        assert b'Test Employee' in response.content
        
        url = reverse('admin:api_employee_change', args=[employee.id])
        response = client.get(url)
        assert response.status_code == 200
        assert b'Test Employee' in response.content
    
    def test_equipment_admin(self, client, admin_user):
        """Test Equipment admin interface"""
        client.force_login(admin_user)
        
        equipment = Equipment.objects.create(
            name='Test Equipment',
            equipment_type='mrt'
        )
        
        url = reverse('admin:api_equipment_changelist')
        response = client.get(url)
        assert response.status_code == 200
        assert b'Test Equipment' in response.content
        
        url = reverse('admin:api_equipment_change', args=[equipment.id])
        response = client.get(url)
        assert response.status_code == 200
        assert b'Test Equipment' in response.content
    
    def test_schedule_admin(self, client, admin_user):
        """Test Schedule admin interface"""
        client.force_login(admin_user)
        
        user = CustomUser.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            role='staff'
        )
        
        equipment = Equipment.objects.create(
            name='Test Equipment',
            equipment_type='mrt'
        )
        
        schedule = Schedule.objects.create(
            employee=employee,
            equipment=equipment,
            shift_type='morning',
            date=timezone.now().date()
        )
        
        url = reverse('admin:api_schedule_changelist')
        response = client.get(url)
        assert response.status_code == 200
        
        url = reverse('admin:api_schedule_change', args=[schedule.id])
        response = client.get(url)
        assert response.status_code == 200
    
    def test_time_off_request_admin(self, client, admin_user):
        """Test TimeOffRequest admin interface"""
        client.force_login(admin_user)
        
        user = CustomUser.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            role='staff'
        )
        
        today = timezone.now().date()
        next_week = today + timezone.timedelta(days=7)
        
        time_off = TimeOffRequest.objects.create(
            employee=employee,
            start_date=today,
            end_date=next_week,
            reason='Vacation',
            priority='medium',
            status='pending'
        )
        
        url = reverse('admin:api_timeoffrequest_changelist')
        response = client.get(url)
        assert response.status_code == 200
        
        url = reverse('admin:api_timeoffrequest_change', args=[time_off.id])
        response = client.get(url)
        assert response.status_code == 200 