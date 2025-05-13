import pytest
from django.core.management import call_command
from io import StringIO
from api.models import Employee, Equipment, EmployeeEquipmentSkill, CustomUser

@pytest.mark.django_db
class TestInitializeDBCommand:
    def test_command_output(self):
        """Test that the initialize_db command runs without errors and creates expected data"""
        out = StringIO()
        call_command('initialize_db', stdout=out)
        output = out.getvalue()
        assert 'Starting database initialization' in output
        assert 'Database initialization completed successfully!' in output
        assert Equipment.objects.filter(name='МРТ аппарат 1').exists()
        assert Equipment.objects.filter(name='РКТ GE аппарат').exists()
        assert Equipment.objects.filter(name='Тошиба РКТ аппарат').exists()
        assert CustomUser.objects.filter(email='manager@hospital.ru').exists()
        assert CustomUser.objects.filter(email='ivanov@hospital.ru').exists()
        manager = Employee.objects.get(email='manager@hospital.ru')
        assert manager.role == 'manager'
        employee = Employee.objects.get(email='ivanov@hospital.ru')
        assert EmployeeEquipmentSkill.objects.filter(
            employee=employee, 
            equipment=Equipment.objects.get(name='МРТ аппарат 1')
        ).exists()

    def test_idempotence(self):
        """Test that running the command multiple times doesn't cause errors"""
        call_command('initialize_db', stdout=StringIO())
        user_count = CustomUser.objects.count()
        equipment_count = Equipment.objects.count()
        call_command('initialize_db', stdout=StringIO())
        assert CustomUser.objects.count() == user_count
        assert Equipment.objects.count() == equipment_count
