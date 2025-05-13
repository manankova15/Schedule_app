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
        
        Schedule.objects.filter(date__gte=start_date, date__lte=end_date).delete()
        
        employees = Employee.objects.all()
        equipment_list = Equipment.objects.all()
        
        current_date = start_date
        while current_date <= end_date:
            for equipment in equipment_list:
                if equipment.shift_morning:
                    available_employees = self._get_available_employees(employees, current_date, 'morning', equipment)
                    if available_employees:
                        employee = random.choice(available_employees)
                        Schedule.objects.create(
                            employee=employee,
                            equipment=equipment,
                            date=current_date,
                            shift_type='morning'
                        )
                
                if equipment.shift_evening:
                    available_employees = self._get_available_employees(employees, current_date, 'evening', equipment)
                    if available_employees:
                        employee = random.choice(available_employees)
                        Schedule.objects.create(
                            employee=employee,
                            equipment=equipment,
                            date=current_date,
                            shift_type='evening'
                        )
                
                if equipment.shift_night:
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
        skilled_employees = []
        for employee in employees:
            skills = EmployeeEquipmentSkill.objects.filter(employee=employee, equipment=equipment)
            if skills.exists():
                skilled_employees.append(employee)
        
        available_employees = []
        for employee in skilled_employees:
            time_off_requests = TimeOffRequest.objects.filter(
                employee=employee,
                start_date__lte=date,
                end_date__gte=date,
                status='approved'
            )
            
            if time_off_requests.exists():
                continue
            
            schedules = Schedule.objects.filter(employee=employee, date=date)
            if schedules.exists():
                continue
            
            if employee.last_work_day_prev_month:
                if date.day == 1:
                    if date.month == 1: 
                        prev_month_year = date.year - 1
                        prev_month = 12  
                    else:
                        prev_month_year = date.year
                        prev_month = date.month - 1
                    
                    if prev_month in [4, 6, 9, 11]:
                        last_day = 30
                    elif prev_month == 2:
                        if prev_month_year % 4 == 0 and (prev_month_year % 100 != 0 or prev_month_year % 400 == 0):
                            last_day = 29
                        else:
                            last_day = 28
                    else:  # 31 день
                        last_day = 31
                    
                    if employee.last_work_day_prev_month.month == prev_month and employee.last_work_day_prev_month.day == last_day:
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
