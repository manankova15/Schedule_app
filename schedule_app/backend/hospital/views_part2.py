from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q

from api.models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill, TimeOffRequest
)
from .views import is_manager, manager_required, generate_calendar_days, get_shift_info

User = get_user_model()

@login_required
@manager_required
def manager_schedule(request):
    """Manager schedule view"""
    # Get view parameters
    view_mode = request.GET.get('view', 'month')
    date_str = request.GET.get('date')
    
    # Parse date or use current date
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
    except ValueError:
        current_date = datetime.now().date()
    
    # Calculate date range
    if view_mode == 'month':
        # Month view
        year = current_date.year
        month = current_date.month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Calculate previous and next month
        if month == 1:
            prev_date = datetime(year - 1, 12, 1).date()
        else:
            prev_date = datetime(year, month - 1, 1).date()
            
        if month == 12:
            next_date = datetime(year + 1, 1, 1).date()
        else:
            next_date = datetime(year, month + 1, 1).date()
            
        # Format header text
        header_text = current_date.strftime('%B %Y')
    else:
        # Week view
        day = current_date.day
        weekday = current_date.weekday()
        start_date = current_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)
        
        # Calculate previous and next week
        prev_date = current_date - timedelta(days=7)
        next_date = current_date + timedelta(days=7)
        
        # Format header text
        if start_date.month == end_date.month:
            header_text = f"{start_date.day} - {end_date.day} {start_date.strftime('%B')}"
        else:
            header_text = f"{start_date.day} {start_date.strftime('%B')} - {end_date.day} {end_date.strftime('%B')}"
    
    # Get all schedules for the date range
    schedules = Schedule.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Prepare calendar data
    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    calendar_days = generate_calendar_days(current_date, view_mode)
    calendar_rows = []
    
    if view_mode == 'month':
        # Split days into rows (weeks)
        for i in range(0, len(calendar_days), 7):
            calendar_rows.append(calendar_days[i:i+7])
    else:
        # Week view is just one row
        calendar_rows = [calendar_days]
    
    # Add shifts to calendar days
    for schedule in schedules:
        date_str = schedule.date.isoformat()
        for row in calendar_rows:
            for cell in row:
                if cell['date'] and cell['date'].isoformat() == date_str:
                    if 'shifts' not in cell:
                        cell['shifts'] = []
                    
                    # Get shift info
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
    
    # Get employees and equipment for the add schedule form
    employees = Employee.objects.all()
    equipment_list = Equipment.objects.all()
    
    context = {
        'view_mode': view_mode,
        'current_date': current_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'header_text': header_text,
        'day_names': day_names,
        'calendar_rows': calendar_rows,
        'schedule': schedules,
        'employees': employees,
        'equipment_list': equipment_list
    }
    
    return render(request, 'schedule/manager_schedule.html', context)

@login_required
@manager_required
def schedule_generator(request):
    """Schedule generator view"""
    error = None
    success = False
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if not start_date or not end_date:
            error = "Пожалуйста, выберите даты начала и окончания"
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if end_date < start_date:
                    error = "Дата окончания не может быть раньше даты начала"
                else:
                    # Calculate date range
                    diff_days = (end_date - start_date).days + 1
                    
                    if diff_days > 31:
                        error = "Период не должен превышать 31 день"
                    else:
                        # Generate schedule
                        from api.views import ScheduleViewSet
                        schedule_viewset = ScheduleViewSet()
                        schedule_viewset.generate_schedule(start_date, end_date)
                        
                        success = True
                        messages.success(request, "Расписание успешно сгенерировано!")
            except ValueError:
                error = "Неверный формат даты"
    
    context = {
        'error': error,
        'success': success,
        'form': {
            'start_date': {'value': request.POST.get('start_date', '')},
            'end_date': {'value': request.POST.get('end_date', '')}
        }
    }
    
    return render(request, 'schedule/schedule_generator.html', context)

@login_required
def time_off_requests(request):
    """Time off requests view"""
    # Get status filter
    status_filter = request.GET.get('status', 'all')
    
    # Get time off requests
    if is_manager(request.user):
        requests = TimeOffRequest.objects.all()
    else:
        requests = TimeOffRequest.objects.filter(employee=request.user.employee)
    
    # Apply status filter
    if status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    # Order by status (pending first) and created_at
    # First, get pending requests
    pending_requests = requests.filter(status='pending').order_by('-created_at')
    # Then, get non-pending requests
    other_requests = requests.exclude(status='pending').order_by('-created_at')
    # Combine the querysets
    requests = list(pending_requests) + list(other_requests)
    
    context = {
        'requests': requests,
        'status_filter': status_filter,
        'is_manager': is_manager(request.user)
    }
    
    return render(request, 'time_off/time_off_requests.html', context)

@login_required
def time_off_request_new(request):
    """New time off request form"""
    error = None
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')
        priority = request.POST.get('priority', 'low')
        
        if not start_date or not end_date or not reason:
            error = "Пожалуйста, заполните все обязательные поля"
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if end_date < start_date:
                    error = "Дата окончания не может быть раньше даты начала"
                else:
                    # Create time off request
                    TimeOffRequest.objects.create(
                        employee=request.user.employee,
                        start_date=start_date,
                        end_date=end_date,
                        reason=reason,
                        priority=priority
                    )
                    
                    messages.success(request, "Запрос на отгул успешно создан!")
                    return redirect('time_off_requests')
            except ValueError:
                error = "Неверный формат даты"
    
    context = {
        'form': {
            'start_date': {'value': request.POST.get('start_date', ''), 'errors': [error] if error else []},
            'end_date': {'value': request.POST.get('end_date', ''), 'errors': []},
            'reason': {'value': request.POST.get('reason', ''), 'errors': []},
            'priority': {'value': request.POST.get('priority', 'low'), 'errors': []}
        }
    }
    
    return render(request, 'time_off/time_off_form.html', context)

@login_required
@require_POST
def delete_time_off_request(request, request_id):
    """Delete time off request"""
    time_off_request = get_object_or_404(TimeOffRequest, id=request_id)
    
    # Check if user is the owner of the request
    if time_off_request.employee.user != request.user:
        messages.error(request, "У вас нет прав для удаления этого запроса.")
        return redirect('time_off_requests')
    
    # Check if request is pending
    if time_off_request.status != 'pending':
        messages.error(request, "Можно удалять только запросы со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
    # Delete request
    time_off_request.delete()
    messages.success(request, "Запрос на отгул успешно удален.")
    
    return redirect('time_off_requests')

@login_required
@manager_required
@require_POST
def approve_time_off_request(request, request_id):
    """Approve time off request"""
    time_off_request = get_object_or_404(TimeOffRequest, id=request_id)
    
    # Check if request is pending
    if time_off_request.status != 'pending':
        messages.error(request, "Можно одобрять только запросы со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
    # Update request
    time_off_request.status = 'approved'
    time_off_request.manager_comment = request.POST.get('comment', '')
    time_off_request.save()
    
    messages.success(request, "Запрос на отгул успешно одобрен.")
    
    return redirect('time_off_requests')

@login_required
@manager_required
@require_POST
def reject_time_off_request(request, request_id):
    """Reject time off request"""
    time_off_request = get_object_or_404(TimeOffRequest, id=request_id)
    
    # Check if request is pending
    if time_off_request.status != 'pending':
        messages.error(request, "Можно отклонять только запросы со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
    # Update request
    time_off_request.status = 'rejected'
    time_off_request.manager_comment = request.POST.get('comment', '')
    time_off_request.save()
    
    messages.success(request, "Запрос на отгул успешно отклонен.")
    
    return redirect('time_off_requests')

@login_required
@manager_required
@require_POST
def update_time_off_request_priority(request, request_id):
    """Update time off request priority"""
    time_off_request = get_object_or_404(TimeOffRequest, id=request_id)
    
    # Check if request is pending
    if time_off_request.status != 'pending':
        messages.error(request, "Можно изменять приоритет только у запросов со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
    # Update request
    priority = request.POST.get('priority')
    if priority not in ['low', 'medium', 'high']:
        messages.error(request, "Неверное значение приоритета.")
        return redirect('time_off_requests')
    
    time_off_request.priority = priority
    time_off_request.save()
    
    messages.success(request, "Приоритет запроса на отгул успешно обновлен.")
    
    return redirect('time_off_requests')

@login_required
@manager_required
@require_POST
def create_schedule_entry(request):
    """Create schedule entry"""
    date = request.POST.get('date')
    employee_id = request.POST.get('employee')
    equipment_id = request.POST.get('equipment')
    shift_type = request.POST.get('shift_type')
    
    if not date or not employee_id or not equipment_id or not shift_type:
        messages.error(request, "Пожалуйста, заполните все поля.")
        return redirect('manager_schedule')
    
    try:
        date = datetime.strptime(date, '%Y-%m-%d').date()
        employee = Employee.objects.get(id=employee_id)
        equipment = Equipment.objects.get(id=equipment_id)
        
        # Check if employee already has a schedule for this date
        if Schedule.objects.filter(employee=employee, date=date).exists():
            messages.error(request, f"Сотрудник {employee.full_name} уже имеет смену на эту дату.")
            return redirect('manager_schedule')
        
        # Check if employee's shift availability allows this shift
        if employee.shift_availability == 'morning_only' and shift_type != 'morning':
            messages.error(request, f"Сотрудник {employee.full_name} может работать только в утреннюю смену.")
            return redirect('manager_schedule')
        
        if employee.shift_availability == 'day_only' and shift_type == 'night':
            messages.error(request, f"Сотрудник {employee.full_name} не может работать в ночную смену.")
            return redirect('manager_schedule')
        
        # Create schedule entry
        Schedule.objects.create(
            employee=employee,
            equipment=equipment,
            shift_type=shift_type,
            date=date
        )
        
        messages.success(request, "Смена успешно добавлена.")
    except (ValueError, Employee.DoesNotExist, Equipment.DoesNotExist):
        messages.error(request, "Произошла ошибка при добавлении смены.")
    
    return redirect('manager_schedule')

@login_required
@manager_required
@require_POST
def delete_schedule_entry(request, entry_id):
    """Delete schedule entry"""
    schedule_entry = get_object_or_404(Schedule, id=entry_id)
    
    # Delete entry
    schedule_entry.delete()
    messages.success(request, "Смена успешно удалена.")
    
    return redirect('manager_schedule')

@login_required
@manager_required
def employees(request):
    """Employees list view"""
    employees = Employee.objects.all().order_by('full_name')
    equipment_list = Equipment.objects.all()
    
    context = {
        'employees': employees,
        'equipment_list': equipment_list
    }
    
    return render(request, 'employees/employee_list.html', context)

@login_required
@manager_required
@require_POST
def create_employee(request):
    """Create employee"""
    try:
        # Create user
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if User.objects.filter(email=username).exists():
            messages.error(request, f"Пользователь с email {username} уже существует.")
            return redirect('employees')
        
        user = User.objects.create_user(email=username, password=password)
        
        # Create employee
        employee = Employee.objects.create(
            user=user,
            full_name=request.POST.get('full_name'),
            email=user.email,
            phone=request.POST.get('phone'),
            position=request.POST.get('position'),
            rate=request.POST.get('rate'),
            role=request.POST.get('role'),
            shift_availability=request.POST.get('shift_availability', 'all_shifts')
        )
        
        # Set last work day if provided
        last_work_day = request.POST.get('last_work_day_prev_month')
        if last_work_day:
            employee.last_work_day_prev_month = datetime.strptime(last_work_day, '%Y-%m-%d').date()
            employee.save()
        
        # Add equipment skills
        for equipment in Equipment.objects.all():
            skill_level = request.POST.get(f'skill_{equipment.id}')
            if skill_level and skill_level != 'none':
                EmployeeEquipmentSkill.objects.create(
                    employee=employee,
                    equipment=equipment,
                    skill_level=skill_level
                )
        
        messages.success(request, f"Сотрудник {employee.full_name} успешно создан.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при создании сотрудника: {str(e)}")
    
    return redirect('employees')

@login_required
@manager_required
@require_POST
def update_employee(request, employee_id):
    """Update employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    try:
        # Update employee
        employee.full_name = request.POST.get('full_name')
        employee.email = request.POST.get('email')
        employee.phone = request.POST.get('phone')
        employee.position = request.POST.get('position')
        employee.rate = request.POST.get('rate')
        employee.role = request.POST.get('role')
        employee.shift_availability = request.POST.get('shift_availability', 'all_shifts')
        
        # Set last work day if provided
        last_work_day = request.POST.get('last_work_day_prev_month')
        if last_work_day:
            employee.last_work_day_prev_month = datetime.strptime(last_work_day, '%Y-%m-%d').date()
        else:
            employee.last_work_day_prev_month = None
        
        employee.save()
        
        # Update equipment skills
        # First, remove all existing skills
        EmployeeEquipmentSkill.objects.filter(employee=employee).delete()
        
        # Then add new skills
        for equipment in Equipment.objects.all():
            skill_level = request.POST.get(f'skill_{equipment.id}')
            if skill_level and skill_level != 'none':
                EmployeeEquipmentSkill.objects.create(
                    employee=employee,
                    equipment=equipment,
                    skill_level=skill_level
                )
        
        messages.success(request, f"Сотрудник {employee.full_name} успешно обновлен.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при обновлении сотрудника: {str(e)}")
    
    return redirect('employees')

@login_required
@manager_required
@require_POST
def delete_employee(request, employee_id):
    """Delete employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    try:
        # Delete user if exists
        if employee.user:
            employee.user.delete()
        
        # Delete employee
        employee.delete()
        
        messages.success(request, "Сотрудник успешно удален.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при удалении сотрудника: {str(e)}")
    
    return redirect('employees')

@login_required
@manager_required
def equipment(request):
    """Equipment list view"""
    equipment_list = Equipment.objects.all().order_by('name')
    
    context = {
        'equipment_list': equipment_list
    }
    
    return render(request, 'equipment/equipment_list.html', context)

@login_required
@manager_required
@require_POST
def create_equipment(request):
    """Create equipment"""
    try:
        # Create equipment
        equipment = Equipment.objects.create(
            name=request.POST.get('name'),
            equipment_type=request.POST.get('equipment_type'),
            shift_morning='shift_morning' in request.POST,
            shift_evening='shift_evening' in request.POST,
            shift_night='shift_night' in request.POST
        )
        
        messages.success(request, f"Оборудование {equipment.name} успешно создано.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при создании оборудования: {str(e)}")
    
    return redirect('equipment')

@login_required
@manager_required
@require_POST
def update_equipment(request, equipment_id):
    """Update equipment"""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    try:
        # Update equipment
        equipment.name = request.POST.get('name')
        equipment.equipment_type = request.POST.get('equipment_type')
        equipment.shift_morning = 'shift_morning' in request.POST
        equipment.shift_evening = 'shift_evening' in request.POST
        equipment.shift_night = 'shift_night' in request.POST
        equipment.save()
        
        messages.success(request, f"Оборудование {equipment.name} успешно обновлено.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при обновлении оборудования: {str(e)}")
    
    return redirect('equipment')

@login_required
@manager_required
@require_POST
def delete_equipment(request, equipment_id):
    """Delete equipment"""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    try:
        # Delete equipment
        equipment.delete()
        
        messages.success(request, "Оборудование успешно удалено.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при удалении оборудования: {str(e)}")
    
    return redirect('equipment')