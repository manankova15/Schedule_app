from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from datetime import datetime, timedelta
import random

from .models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill, TimeOffRequest
)
from .serializers import (
    EmployeeSerializer, EquipmentSerializer, ScheduleSerializer,
    EmployeeEquipmentSkillSerializer, TimeOffRequestSerializer,
    UserSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'employee') and user.employee.role == 'manager':
            return Employee.objects.all()
        return Employee.objects.filter(user=user)

class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'employee') and user.employee.role == 'manager':
            return Schedule.objects.all()
        return Schedule.objects.filter(employee__user=user)
    
    @action(detail=False, methods=['post'])
    def generate_schedule(self, request):
        """Generate schedule for a date range"""
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return Response({"error": "Start date and end date are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete existing schedules in the date range
        Schedule.objects.filter(date__gte=start_date, date__lte=end_date).delete()
        
        # Get all employees and equipment
        employees = Employee.objects.all()
        equipment_list = Equipment.objects.all()
        
        # Generate schedule for each day
        current_date = start_date
        while current_date <= end_date:
            # For each equipment
            for equipment in equipment_list:
                # Morning shift (8:00-14:00)
                if equipment.shift_morning:
                    # Find employees who can work on this equipment in the morning
                    available_employees = self._get_available_employees(employees, current_date, 'morning', equipment)
                    if available_employees:
                        employee = random.choice(available_employees)
                        Schedule.objects.create(
                            employee=employee,
                            equipment=equipment,
                            date=current_date,
                            shift_type='morning'
                        )
                
                # Evening shift (14:00-20:00)
                if equipment.shift_evening:
                    # Find employees who can work on this equipment in the evening
                    available_employees = self._get_available_employees(employees, current_date, 'evening', equipment)
                    if available_employees:
                        employee = random.choice(available_employees)
                        Schedule.objects.create(
                            employee=employee,
                            equipment=equipment,
                            date=current_date,
                            shift_type='evening'
                        )
                
                # Night shift (20:00-8:00)
                if equipment.shift_night:
                    # Find employees who can work on this equipment at night
                    available_employees = self._get_available_employees(employees, current_date, 'night', equipment)
                    if available_employees:
                        employee = random.choice(available_employees)
                        Schedule.objects.create(
                            employee=employee,
                            equipment=equipment,
                            date=current_date,
                            shift_type='night'
                        )
            
            current_date += timedelta(days=1)
        
        return Response({"message": "Schedule generated successfully"}, status=status.HTTP_200_OK)
    
    def _get_available_employees(self, employees, date, shift_type, equipment):
        """Get available employees for a specific date, shift and equipment"""
        # Filter employees who have the skills to work on this equipment
        skilled_employees = []
        for employee in employees:
            skills = EmployeeEquipmentSkill.objects.filter(employee=employee, equipment=equipment)
            if skills.exists():
                skilled_employees.append(employee)
        
        # Filter out employees who already have a schedule for this date
        available_employees = []
        for employee in skilled_employees:
            # Check if employee has a time off request for this date
            time_off_requests = TimeOffRequest.objects.filter(
                employee=employee,
                start_date__lte=date,
                end_date__gte=date,
                status='approved'
            )
            
            if time_off_requests.exists():
                continue
            
            # Check if employee already has a schedule for this date
            schedules = Schedule.objects.filter(employee=employee, date=date)
            if schedules.exists():
                continue
            
            # Check if employee worked the day before (to avoid consecutive shifts)
            if employee.last_work_day_prev_month:
                if date == datetime(date.year, date.month, 1).date() and employee.last_work_day_prev_month == datetime(date.year, date.month - 1 if date.month > 1 else 12, 1).date().replace(day=1).replace(day=28):
                    continue
            
            prev_day_schedules = Schedule.objects.filter(employee=employee, date=date - timedelta(days=1))
            if prev_day_schedules.exists():
                continue
            
            available_employees.append(employee)
        
        return available_employees

class EmployeeEquipmentSkillViewSet(viewsets.ModelViewSet):
    queryset = EmployeeEquipmentSkill.objects.all()
    serializer_class = EmployeeEquipmentSkillSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'employee') and user.employee.role == 'manager':
            return EmployeeEquipmentSkill.objects.all()
        return EmployeeEquipmentSkill.objects.filter(employee__user=user)

class TimeOffRequestViewSet(viewsets.ModelViewSet):
    queryset = TimeOffRequest.objects.all()
    serializer_class = TimeOffRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'employee') and user.employee.role == 'manager':
            return TimeOffRequest.objects.all()
        return TimeOffRequest.objects.filter(employee__user=user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a time off request"""
        time_off_request = self.get_object()
        time_off_request.status = 'approved'
        time_off_request.save()
        return Response({"message": "Time off request approved"}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a time off request"""
        time_off_request = self.get_object()
        time_off_request.status = 'rejected'
        time_off_request.save()
        return Response({"message": "Time off request rejected"}, status=status.HTTP_200_OK)
