from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView, 
    PasswordResetConfirmView, PasswordResetCompleteView,
    PasswordChangeView
)

from api.models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill, TimeOffRequest
)
from api.views import ScheduleViewSet
from .forms import (
    CustomUserCreationForm, ManagerRegistrationForm, EmployeeRegistrationForm,
    CustomPasswordResetForm, CustomSetPasswordForm, CustomPasswordChangeForm,
    ProfileForm
)

User = get_user_model()

MANAGER_REGISTRATION_CODE = "manager123"
EMPLOYEE_REGISTRATION_CODE = "employee123"

def is_manager(user):
    if not hasattr(user, 'employee'):
        return False
    return user.employee.role == 'manager'

def manager_required(view_func):
    """Decorator for views that require manager role"""
    def wrapper(request, *args, **kwargs):
        if not is_manager(request.user):
            messages.error(request, "У вас нет прав для доступа к этой странице.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def logout_view(request):
    logout(request)
    messages.success(request, "Вы успешно вышли из системы.")
    return render(request, 'registration/logout.html')

def register(request):
    if request.method == 'POST':
        form = EmployeeRegistrationForm(request.POST)
        registration_code = request.POST.get('registration_code')
        role = 'staff'
        
        if registration_code == MANAGER_REGISTRATION_CODE:
            role = 'manager'
        elif registration_code != EMPLOYEE_REGISTRATION_CODE:
            messages.error(request, "Неверный код регистрации. Пожалуйста, проверьте код и попробуйте снова.")
            return render(request, 'registration/register.html', {'form': form})
        
        if form.is_valid():
            user = form.save()
            
            full_name = form.cleaned_data.get('full_name')
            
            Employee.objects.create(
                user=user,
                full_name=full_name,
                email=user.email,
                phone=form.cleaned_data.get('phone') if role == 'staff' else None,
                role=role
            )
            
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            user = authenticate(email=email, password=password)
            login(request, user)
            return redirect('home')
    else:
        form = EmployeeRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def register_manager(request):
    return redirect('register')

@login_required
def profile(request):
    employee = request.user.employee
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль успешно обновлен!")
            return redirect('profile')
    else:
        form = ProfileForm(instance=employee)
    
    context = {
        'form': form,
        'employee': employee
    }
    
    return render(request, 'profile/profile.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Пароль успешно изменен!")
            return redirect('profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    context = {
        'form': form
    }
    
    return render(request, 'profile/change_password.html', context)

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = '/password-reset/done/'

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'registration/password_reset_confirm.html'
    success_url = '/password-reset/complete/'

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'

@login_required
def home(request):
    """Home page - redirects to appropriate page based on user role"""
    if is_manager(request):
        return redirect('manager_schedule')
    else:
        return redirect('my_schedule')

@login_required
def my_schedule(request):
    view_mode = request.GET.get('view', 'month')
    date_str = request.GET.get('date')
    
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        current_date = timezone.now().date()
    
    if view_mode == 'month':
        year = current_date.year
        month = current_date.month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        if month == 1:
            prev_date = datetime(year - 1, 12, 1).date()
        else:
            prev_date = datetime(year, month - 1, 1).date()
            
        if month == 12:
            next_date = datetime(year + 1, 1, 1).date()
        else:
            next_date = datetime(year, month + 1, 1).date()
            
        header_text = current_date.strftime('%B %Y')
    else:
        day = current_date.day
        weekday = current_date.weekday()
        start_date = current_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)
        
        prev_date = current_date - timedelta(days=7)
        next_date = current_date + timedelta(days=7)
        
        if start_date.month == end_date.month:
            header_text = f"{start_date.day} - {end_date.day} {start_date.strftime('%B')}"
        else:
            header_text = f"{start_date.day} {start_date.strftime('%B')} - {end_date.day} {end_date.strftime('%B')}"
    
    employee = request.user.employee
    schedules = Schedule.objects.filter(
        employee=employee,
        date__gte=start_date,
        date__lte=end_date
    )
    
    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    calendar_days = generate_calendar_days(current_date, view_mode)
    calendar_rows = []
    
    if view_mode == 'month':
        for i in range(0, len(calendar_days), 7):
            calendar_rows.append(calendar_days[i:i+7])
    else:
        calendar_rows = [calendar_days]
    
    for schedule in schedules:
        date_str = schedule.date.isoformat()
        for row in calendar_rows:
            for cell in row:
                if cell['date'] and cell['date'].isoformat() == date_str:
                    if 'shifts' not in cell:
                        cell['shifts'] = []
                    
                    shift_info = get_shift_info(schedule.shift_type)
                    
                    cell['shifts'].append({
                        'id': schedule.id,
                        'employee_name': schedule.employee.full_name,
                        'equipment_name': schedule.equipment.name,
                        'shift_type': schedule.shift_type,
                        'shift_label': shift_info['label'],
                        'shift_time': shift_info['time'],
                        'color': shift_info['color'],
                        'date': schedule.date
                    })
    
    context = {
        'view_mode': view_mode,
        'current_date': current_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'header_text': header_text,
        'day_names': day_names,
        'calendar_rows': calendar_rows,
        'schedule': schedules
    }
    
    return render(request, 'schedule/employee_schedule.html', context)

def generate_calendar_days(current_date, view_mode):
    """Generate calendar days for the given date and view mode"""
    year = current_date.year
    month = current_date.month
    
    if view_mode == 'month':
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # 0 = Monday, 6 = Sunday
        first_day_of_week = first_day.weekday()
        
        days = []
        
        for i in range(first_day_of_week):
            days.append({'date': None, 'is_current_month': False})
        
        for day in range(1, last_day.day + 1):
            date = datetime(year, month, day).date()
            days.append({
                'date': date,
                'is_current_month': True,
                'is_today': date == datetime.now().date()
            })
        
        last_day_of_week = last_day.weekday()
        for i in range(6 - last_day_of_week):
            days.append({'date': None, 'is_current_month': False})
        
        return days
    else:
        day = current_date.day
        weekday = current_date.weekday()
        start_day = current_date - timedelta(days=weekday)
        
        days = []
        for i in range(7):
            date = start_day + timedelta(days=i)
            days.append({
                'date': date,
                'is_current_month': date.month == current_date.month,
                'is_today': date == datetime.now().date()
            })
        
        return days

def get_shift_info(shift_type):
    shift_types = {
        'morning': {'label': 'Утро', 'time': '8:00-14:00', 'color': 'success'},
        'evening': {'label': 'Вечер', 'time': '14:00-20:00', 'color': 'primary'},
        'night': {'label': 'Ночь', 'time': '20:00-8:00', 'color': 'danger'}
    }
    
    return shift_types.get(shift_type, {'label': shift_type, 'time': '', 'color': 'secondary'})

from .views_part2 import (
    manager_schedule, schedule_generator, time_off_requests, time_off_request_new,
    delete_time_off_request, approve_time_off_request, reject_time_off_request,
    update_time_off_request_priority, create_schedule_entry, delete_schedule_entry,
    employees, create_employee, update_employee, delete_employee,
    equipment, create_equipment, update_equipment, delete_equipment
)
