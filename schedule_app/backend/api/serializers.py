from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Employee, Equipment, Schedule, EmployeeEquipmentSkill, TimeOffRequest

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'is_staff', 'is_active', 'date_joined']
        read_only_fields = ['is_staff', 'is_active', 'date_joined']

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'

class EmployeeEquipmentSkillSerializer(serializers.ModelSerializer):
    equipment_name = serializers.ReadOnlyField(source='equipment.name')
    
    class Meta:
        model = EmployeeEquipmentSkill
        fields = ['id', 'employee', 'equipment', 'equipment_name', 'skill_level']

class EmployeeSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    equipment_skills = EmployeeEquipmentSkillSerializer(many=True, read_only=True)
    
    class Meta:
        model = Employee
        fields = ['id', 'user', 'user_email', 'full_name', 'email', 'phone', 'position', 
                 'rate', 'role', 'last_work_day_prev_month', 'equipment_skills']

class ScheduleSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.full_name')
    equipment_name = serializers.ReadOnlyField(source='equipment.name')
    
    class Meta:
        model = Schedule
        fields = ['id', 'employee', 'employee_name', 'equipment', 'equipment_name', 
                 'shift_type', 'date']

class TimeOffRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.full_name')
    
    class Meta:
        model = TimeOffRequest
        fields = ['id', 'employee', 'employee_name', 'start_date', 'end_date', 
                 'reason', 'priority', 'status', 'manager_comment', 'created_at']
