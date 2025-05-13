import pytest
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from api.models import (
    Employee, Equipment, EmployeeEquipmentSkill,
    Schedule, TimeOffRequest, CustomUserManager
)

User = get_user_model()

@pytest.mark.django_db
class TestCustomUserManager:
    def test_create_user_without_email(self):
        """Тестирование создания пользователя без email"""
        manager = CustomUserManager()
        with pytest.raises(ValueError, match="The Email field must be set"):
            manager.create_user(email="", password="password123")
    
    def test_create_superuser_with_is_staff_false(self):
        """Тестирование создания суперпользователя с is_staff=False"""
        manager = CustomUserManager()
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            manager.create_superuser(
                email="admin@example.com",
                password="adminpass123",
                is_staff=False
            )
    
    def test_create_superuser_with_is_superuser_false(self):
        """Тестирование создания суперпользователя с is_superuser=False"""
        manager = CustomUserManager()
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            manager.create_superuser(
                email="admin@example.com",
                password="adminpass123",
                is_superuser=False
            )

@pytest.mark.django_db
class TestEmployeeAdditional:
    def test_employee_str_method(self):
        """Тестирование строкового представления сотрудника"""
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
        
        assert str(employee) == 'Test Employee'
    
    def test_employee_with_all_fields(self):
        """Тестирование создания сотрудника со всеми полями"""
        user = User.objects.create_user(
            email='employee@example.com',
            password='password123'
        )
        
        employee = Employee.objects.create(
            user=user,
            full_name='Test Employee',
            email='employee@example.com',
            phone='1234567890',
            position='Doctor',
            rate=1.5,
            role='manager',
            shift_availability='morning_only',
            last_work_day_prev_month=timezone.now().date()
        )
        
        assert employee.phone == '1234567890'
        assert employee.position == 'Doctor'
        assert employee.rate == 1.5
        assert employee.role == 'manager'
        assert employee.shift_availability == 'morning_only'
        assert employee.last_work_day_prev_month == timezone.now().date()

@pytest.mark.django_db
class TestEquipmentAdditional:
    def test_equipment_str_method(self):
        """Тестирование строкового представления оборудования"""
        equipment = Equipment.objects.create(
            name='MRI Scanner',
            equipment_type='mrt'
        )
        
        assert str(equipment) == 'MRI Scanner'
    
    def test_equipment_with_shifts(self):
        """Тестирование оборудования с различными сменами"""
        equipment1 = Equipment.objects.create(
            name='Scanner 1',
            equipment_type='mrt',
            shift_morning=True,
            shift_evening=False,
            shift_night=False
        )
        
        equipment2 = Equipment.objects.create(
            name='Scanner 2',
            equipment_type='rkt_ge',
            shift_morning=False,
            shift_evening=True,
            shift_night=True
        )
        
        assert equipment1.shift_morning is True
        assert equipment1.shift_evening is False
        assert equipment1.shift_night is False
        
        assert equipment2.shift_morning is False
        assert equipment2.shift_evening is True
        assert equipment2.shift_night is True

@pytest.mark.django_db
class TestScheduleAdditional:
    def test_schedule_str_method(self):
        """Тестирование строкового представления расписания"""
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
            name='CT Scanner',
            equipment_type='rkt_ge'
        )
        
        schedule_morning = Schedule.objects.create(
            employee=employee,
            equipment=equipment,
            shift_type='morning',
            date=timezone.now().date()
        )
        
        assert "Test Employee - CT Scanner - Утро (8:00-14:00)" in str(schedule_morning)
        
        schedule_evening = Schedule.objects.create(
            employee=employee,
            equipment=equipment,
            shift_type='evening',
            date=timezone.now().date() + timezone.timedelta(days=1)
        )
        
        assert "Test Employee - CT Scanner - Вечер (14:00-20:00)" in str(schedule_evening)
        
        schedule_night = Schedule.objects.create(
            employee=employee,
            equipment=equipment,
            shift_type='night',
            date=timezone.now().date() + timezone.timedelta(days=2)
        )
        
        assert "Test Employee - CT Scanner - Ночь (20:00-8:00)" in str(schedule_night)

@pytest.mark.django_db
class TestTimeOffRequestAdditional:
    def test_timeoffrequest_str_method(self):
        """Тестирование строкового представления запроса на отгул"""
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
        
        expected_str = f"{employee.full_name} - {today} to {next_week} - На рассмотрении"
        assert expected_str in str(time_off)
    
    def test_timeoffrequest_with_all_statuses(self):
        """Тестирование запроса на отгул со всеми статусами"""
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
        
        today = timezone.now().date()
        
        time_off_pending = TimeOffRequest.objects.create(
            employee=employee,
            start_date=today,
            end_date=today + timezone.timedelta(days=1),
            reason='Reason 1',
            priority='low',
            status='pending'
        )
        
        time_off_approved = TimeOffRequest.objects.create(
            employee=employee,
            start_date=today + timezone.timedelta(days=2),
            end_date=today + timezone.timedelta(days=3),
            reason='Reason 2',
            priority='medium',
            status='approved'
        )
        
        time_off_rejected = TimeOffRequest.objects.create(
            employee=employee,
            start_date=today + timezone.timedelta(days=4),
            end_date=today + timezone.timedelta(days=5),
            reason='Reason 3',
            priority='high',
            status='rejected',
            manager_comment='Rejected due to high workload'
        )
        
        assert time_off_pending.status == 'pending'
        assert time_off_approved.status == 'approved'
        assert time_off_rejected.status == 'rejected'
        assert time_off_rejected.manager_comment == 'Rejected due to high workload' 