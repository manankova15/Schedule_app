from datetime import datetime, timedelta, date
import calendar
import heapq
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum, Count, Case, When, IntegerField
import random

from api.models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill, TimeOffRequest,
    ScheduleVersion
)
from .views import is_manager, manager_required, generate_calendar_days, get_shift_info

User = get_user_model()

logger = logging.getLogger(__name__)

def get_working_days_in_month(year, month):
    cal = calendar.monthcalendar(year, month)
    working_days = 0
    for week in cal:
        for day in week:
            if day != 0 and calendar.weekday(year, month, day) < 5:
                working_days += 1
    return working_days

def get_available_employees(employees, date, shift_type, equipment):
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
                else:
                    last_day = 31
                
                if (employee.last_work_day_prev_month.month == prev_month and
                    employee.last_work_day_prev_month.day == last_day):
                    continue
        
        prev_day_schedules = Schedule.objects.filter(employee=employee, date=date - timedelta(days=1))
        if prev_day_schedules.exists():
            continue
        
        if employee.shift_availability == 'morning_only' and shift_type != 'morning':
            continue
        
        if employee.shift_availability == 'day_only' and shift_type == 'night':
            continue
        
        available_employees.append(employee)
    
    return available_employees

@login_required
@manager_required
def manager_schedule(request):
    view_mode = request.GET.get('view', 'month')
    date_str = request.GET.get('date')
    
    employee_ids = request.GET.get('employees', '').split(',') if request.GET.get('employees') else []
    equipment_ids = request.GET.get('equipment', '').split(',') if request.GET.get('equipment') else []
    shift_types = request.GET.get('shifts', '').split(',') if request.GET.get('shifts') else []
    
    employee_ids = [id for id in employee_ids if id]
    equipment_ids = [id for id in equipment_ids if id]
    shift_types = [shift for shift in shift_types if shift]
    
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
    except ValueError:
        current_date = datetime.now().date()
    
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
            header_text = (
                f"{start_date.day} {start_date.strftime('%B')} - "
                f"{end_date.day} {end_date.strftime('%B')}"
            )
    
    schedules = Schedule.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )
    
    if employee_ids:
        schedules = schedules.filter(employee__id__in=employee_ids)
    
    if equipment_ids:
        schedules = schedules.filter(equipment__id__in=equipment_ids)
    
    if shift_types:
        schedules = schedules.filter(shift_type__in=shift_types)
    
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
    error = None
    success = False
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        logger.info(f"Schedule generation requested by {request.user.email} for period {start_date} to {end_date}")
        
        if not start_date or not end_date:
            error = "Пожалуйста, выберите даты начала и окончания"
            logger.warning(f"Schedule generation failed: missing dates")
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if end_date < start_date:
                    error = "Дата окончания не может быть раньше даты начала"
                    logger.warning(f"Schedule generation failed: end date before start date")
                else:
                    diff_days = (end_date - start_date).days + 1
                    
                    if diff_days > 31:
                        error = "Период не должен превышать 31 день"
                        logger.warning(f"Schedule generation failed: period too long ({diff_days} days)")
                    else:
                        version_name = f"Schedule {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        logger.info(f"Creating schedule version: {version_name}")
                        
                        current_schedules = Schedule.objects.filter(date__gte=start_date, date__lte=end_date)
                        if current_schedules.exists():
                            try:
                                schedule_version = ScheduleVersion.objects.create(
                                    name=version_name,
                                    created_by=request.user,
                                    start_date=start_date,
                                    end_date=end_date
                                )
                                
                                for schedule in current_schedules:
                                    schedule_version.entries.create(
                                        employee=schedule.employee,
                                        equipment=schedule.equipment,
                                        date=schedule.date,
                                        shift_type=schedule.shift_type
                                    )
                                logger.info(f"Saved {current_schedules.count()} schedule entries to version {version_name}")
                            except Exception as e:
                                logger.error(f"Failed to create schedule version: {str(e)}")
                        
                        Schedule.objects.filter(date__gte=start_date, date__lte=end_date).delete()
                        logger.info(f"Deleted existing schedule for period {start_date} to {end_date}")
                        all_employees = Employee.objects.all()
                        employees = []
                        for employee in all_employees:
                            if EmployeeEquipmentSkill.objects.filter(employee=employee).exists():
                                employees.append(employee)
                        equipment_list = Equipment.objects.all()
                        day_workers = []
                        on_call_workers = []
                        regular_workers = []
                        
                        for employee in employees:
                            if employee.shift_availability == 'morning_only':
                                day_workers.append(employee)
                            elif employee.shift_availability == 'all_shifts':
                                on_call_workers.append(employee)
                            else:
                                regular_workers.append(employee)
                        
                        employee_nodes = []
                        shift_nodes = []
                        edges = {}
                        
                        current_date = start_date
                        while current_date <= end_date:
                            is_weekend = current_date.weekday() >= 5
                            
                            for equipment in equipment_list:
                                if is_weekend and equipment.equipment_type != 'rkt_ge':
                                    continue
                                
                                if equipment.shift_morning:
                                    shift_nodes.append((current_date, equipment.id, 'morning'))
                                if equipment.shift_evening:
                                    shift_nodes.append((current_date, equipment.id, 'evening'))
                                if equipment.shift_night:
                                    shift_nodes.append((current_date, equipment.id, 'night'))
                            
                            current_date += timedelta(days=1)
                        
                        employee_workload = {employee.id: 0 for employee in employees}
                        
                        for employee in employees:
                            employee_nodes.append(employee.id)
                            employee_shifts = Schedule.objects.filter(
                                employee=employee,
                                date__lt=start_date,
                                date__gte=start_date - timedelta(days=30)
                            ).count()
                            
                            for shift_node in shift_nodes:
                                date, equipment_id, shift_type = shift_node
                                equipment = Equipment.objects.get(id=equipment_id)
                                is_weekend = date.weekday() >= 5
                                
                                weight = -1000
                                
                                skill = EmployeeEquipmentSkill.objects.filter(
                                    employee=employee,
                                    equipment=equipment
                                ).first()
                                
                                if not skill:
                                    continue
                                
                                weight = 0
                                
                                if skill.skill_level == 'primary':
                                    weight += 500
                                else:
                                    weight += 50
                                
                                if employee.shift_availability == 'morning_only':
                                    if shift_type != 'morning':
                                        continue
                                    elif is_weekend:
                                        continue
                                    else:
                                        weight += 300
                                
                                elif employee.shift_availability == 'day_only':
                                    if shift_type == 'night':
                                        continue
                                    elif is_weekend:
                                        continue
                                    else:
                                        weight += 100
                                
                                elif employee.shift_availability == 'all_shifts':
                                    if is_weekend:
                                        has_worked_recently = False
                                        for days_back in range(1, 4):
                                            prev_day = date - timedelta(days=days_back)
                                            prev_shift = Schedule.objects.filter(
                                                employee=employee,
                                                date=prev_day
                                            ).exists()
                                            
                                            if prev_shift:
                                                has_worked_recently = True
                                                break
                                        
                                        if has_worked_recently:
                                            continue
                                        
                                        already_assigned_to_equipment = False
                                        other_shifts_for_equipment = []
                                        
                                        for s_type in ['morning', 'evening', 'night']:
                                            if s_type == shift_type:
                                                continue
                                                
                                            other_shift = (date, equipment_id, s_type)
                                            if other_shift in shift_nodes:
                                                other_shifts_for_equipment.append(other_shift)
                                                
                                                other_schedule = Schedule.objects.filter(
                                                    employee=employee,
                                                    equipment=equipment,
                                                    date=date,
                                                    shift_type=s_type
                                                ).exists()
                                                
                                                if other_schedule:
                                                    already_assigned_to_equipment = True
                                        
                                        if already_assigned_to_equipment:
                                            weight += 5000
                                        elif shift_type == 'morning':
                                            weight += 1000
                                        else:
                                            weight += 800
                                    else:
                                        if shift_type == 'morning':
                                            continue
                                        elif shift_type == 'evening':
                                            has_worked_recently = False
                                            for days_back in range(1, 4):
                                                prev_day = date - timedelta(days=days_back)
                                                prev_shift = Schedule.objects.filter(
                                                    employee=employee,
                                                    date=prev_day
                                                ).exists()
                                                
                                                if prev_shift:
                                                    has_worked_recently = True
                                                    break
                                            
                                            if has_worked_recently:
                                                continue
                                                
                                            weight += 1000
                                            
                                            night_shift = (date, equipment_id, 'night')
                                            if night_shift in shift_nodes:
                                                weight += 2000
                                        elif shift_type == 'night':
                                            evening_shift = (date, equipment_id, 'evening')
                                            evening_schedule = Schedule.objects.filter(
                                                employee=employee,
                                                equipment=equipment,
                                                date=date,
                                                shift_type='evening'
                                            ).exists()
                                            
                                            if evening_schedule:
                                                weight += 5000
                                            else:
                                                continue
                                
                                approved_time_off = TimeOffRequest.objects.filter(
                                    employee=employee,
                                    start_date__lte=date,
                                    end_date__gte=date,
                                    status='approved'
                                ).exists()
                                
                                if approved_time_off:
                                    continue
                                
                                pending_time_off = TimeOffRequest.objects.filter(
                                    employee=employee,
                                    start_date__lte=date,
                                    end_date__gte=date,
                                    status='pending'
                                ).first()
                                
                                if pending_time_off:
                                    if pending_time_off.priority == 'low':
                                        weight -= 200
                                    elif pending_time_off.priority == 'medium':
                                        weight -= 500
                                    elif pending_time_off.priority == 'high':
                                        weight -= 1000
                                        continue
                                
                                prev_day_schedule = Schedule.objects.filter(
                                    employee=employee,
                                    date=date - timedelta(days=1)
                                ).exists()
                                
                                if prev_day_schedule:
                                    weight -= 300
                                
                                for days_back in range(1, 4):
                                    prev_day = date - timedelta(days=days_back)
                                    prev_night_shift = Schedule.objects.filter(
                                        employee=employee,
                                        date=prev_day,
                                        shift_type='night'
                                    ).exists()
                                    
                                    if prev_night_shift:
                                        if days_back < 3:
                                            continue
                                        else:
                                            weight -= 300
                                
                                same_day_schedule = Schedule.objects.filter(
                                    employee=employee,
                                    date=date
                                ).exists()
                                
                                if same_day_schedule:
                                    if employee.shift_availability == 'all_shifts' and is_weekend:
                                        weight += 100
                                    else:
                                        weight -= 500
                                        continue
                                
                                current_date_month = date.month
                                current_date_year = date.year
                                working_days_in_month = get_working_days_in_month(current_date_year, current_date_month)
                                
                                required_hours = working_days_in_month * 6
                                if float(employee.rate) == 1.5:
                                    required_hours = round(required_hours * 1.5)
                                
                                has_any_skill = EmployeeEquipmentSkill.objects.filter(employee=employee).exists()
                                if not has_any_skill:
                                    continue
                                
                                current_hours = 0
                                for s in Schedule.objects.filter(
                                    employee=employee,
                                    date__month=current_date_month,
                                    date__year=current_date_year
                                ):
                                    if s.shift_type == 'morning':
                                        current_hours += 6
                                    elif s.shift_type == 'evening':
                                        current_hours += 6
                                    elif s.shift_type == 'night':
                                        current_hours += 12
                                
                                future_hours = 0
                                for edge, edge_weight in edges.items():
                                    e_id, s_node = edge
                                    if (e_id == employee.id and
                                        s_node[0].month == current_date_month and
                                        s_node[0].year == current_date_year):
                                        if s_node[2] == 'morning':
                                            future_hours += 6
                                        elif s_node[2] == 'evening':
                                            future_hours += 6
                                        elif s_node[2] == 'night':
                                            future_hours += 12
                                
                                shift_hours = 0
                                if shift_type == 'morning':
                                    shift_hours = 6
                                elif shift_type == 'evening':
                                    shift_hours = 6
                                elif shift_type == 'night':
                                    shift_hours = 12
                                
                                total_hours = current_hours + future_hours + shift_hours
                                
                                if total_hours > required_hours + 6:
                                    if total_hours > required_hours + 12:
                                        continue
                                    else:
                                        weight -= (total_hours - required_hours) * 50
                                elif total_hours > required_hours:
                                    weight -= (total_hours - required_hours) * 30
                                elif total_hours < required_hours - 12:
                                    remaining_hours = required_hours - total_hours
                                    weight += min(remaining_hours * 15, 300)
                                elif total_hours < required_hours:
                                    remaining_hours = required_hours - total_hours
                                    weight += min(remaining_hours * 10, 200)
                                else:
                                    weight += 250
                                
                                if shift_type == 'night' and employee.shift_availability == 'all_shifts':
                                    n_nights_for_employee = Schedule.objects.filter(
                                        employee=employee,
                                        shift_type='night',
                                        date__month=current_date_month,
                                        date__year=current_date_year,
                                    ).count()
                                    
                                    total_night_shifts = len([s for s in shift_nodes if s[2] == 'night' and
                                                             s[0].month == current_date_month and
                                                             s[0].year == current_date_year])
                                    
                                    total_on_call_workers = len([e for e in employees if e.shift_availability == 'all_shifts'])
                                    
                                    avg_nights = total_night_shifts / (total_on_call_workers or 1)
                                    
                                    if n_nights_for_employee > avg_nights + 1:
                                        weight -= 200
                                    elif n_nights_for_employee < avg_nights - 1:
                                        weight += 50
                                
                                if equipment.equipment_type == 'rkt_ge':
                                    weight += 20
                                elif equipment.equipment_type in ['mrt', 'rkt_toshiba']:
                                    if is_weekend and shift_type != 'morning':
                                        weight -= 50
                                
                                edges[(employee.id, shift_node)] = weight
                        
                        initial_matching = find_maximum_weighted_matching(employee_nodes, shift_nodes, edges)
                        final_matching = apply_scheduling_rules(
                            initial_matching,
                            employee_nodes,
                            shift_nodes,
                            edges,
                            day_workers,
                            on_call_workers
                        )
                        
                        shifts_by_date_type = {}
                        for employee_id, shift_node in final_matching:
                            date, equipment_id, shift_type = shift_node
                            key = (date, shift_type)
                            if key not in shifts_by_date_type:
                                shifts_by_date_type[key] = []
                            shifts_by_date_type[key].append((employee_id, equipment_id))
                        
                        resolved_matching = []
                        assigned_employees = {}
                        
                        sorted_matching = sorted(final_matching, key=lambda x: x[1][0])
                        
                        for employee_id, shift_node in sorted_matching:
                            date, equipment_id, shift_type = shift_node
                            
                            if date not in assigned_employees:
                                assigned_employees[date] = set()
                            
                            if employee_id in assigned_employees[date]:
                                continue
                            
                            conflict = False
                            for res_employee_id, res_shift_node in resolved_matching:
                                res_date, res_equipment_id, res_shift_type = res_shift_node
                                if res_date == date and res_equipment_id == equipment_id and res_shift_type == shift_type:
                                    conflict = True
                                    break
                            
                            if not conflict:
                                resolved_matching.append((employee_id, shift_node))
                                assigned_employees[date].add(employee_id)
                        
                        assigned_shifts = set(shift_node for _, shift_node in resolved_matching)
                        unassigned_shifts = [s for s in shift_nodes if s not in assigned_shifts]
                        
                        if unassigned_shifts:
                            print(f"WARNING: {len(unassigned_shifts)} shifts are unassigned after conflict resolution. Assigning them now.")
                            
                            for shift_node in unassigned_shifts:
                                date, equipment_id, shift_type = shift_node
                                
                                available_employees = []
                                for employee_id in employee_nodes:
                                    if employee_id not in assigned_employees.get(date, set()):
                                        skill = EmployeeEquipmentSkill.objects.filter(
                                            employee_id=employee_id,
                                            equipment_id=equipment_id
                                        ).exists()
                                        
                                        if skill:
                                            available_employees.append(employee_id)
                                
                                if available_employees:
                                    employee_counts = {}
                                    for e_id in available_employees:
                                        employee_counts[e_id] = sum(1 for _, s in resolved_matching if s[0] == e_id)
                                    
                                    best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
                                    resolved_matching.append((best_employee_id, shift_node))
                                    
                                    if date not in assigned_employees:
                                        assigned_employees[date] = set()
                                    assigned_employees[date].add(best_employee_id)
                                else:
                                    employee_counts = {}
                                    for e_id in employee_nodes:
                                        employee_counts[e_id] = sum(1 for _, s in resolved_matching if s[0] == e_id)
                                    
                                    best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
                                    resolved_matching.append((best_employee_id, shift_node))
                                    
                                    if date not in assigned_employees:
                                        assigned_employees[date] = set()
                                    assigned_employees[date].add(best_employee_id)
                        
                        for employee_id, shift_node in resolved_matching:
                            date, equipment_id, shift_type = shift_node
                            Schedule.objects.create(
                                employee=Employee.objects.get(id=employee_id),
                                equipment=Equipment.objects.get(id=equipment_id),
                                date=date,
                                shift_type=shift_type
                            )
                        
                        success = True
                        logger.info(f"Schedule generation completed successfully for period {start_date} to {end_date}")
                        return redirect('manager_schedule')
            except ValueError:
                error = "Неверный формат даты"
                logger.warning(f"Schedule generation failed: invalid date format")
            except Exception as e:
                error = f"Произошла ошибка при генерации расписания: {str(e)}"
                logger.error(f"Schedule generation failed with error: {str(e)}")
    
    schedule_versions = []
    try:
        schedule_versions = ScheduleVersion.objects.all().order_by('-created_at')
        logger.debug(f"Found {schedule_versions.count()} schedule versions")
    except Exception as e:
        logger.error(f"Failed to retrieve schedule versions: {str(e)}")
    
    context = {
        'error': error,
        'success': success,
        'form': {
            'start_date': {'value': request.POST.get('start_date', '')},
            'end_date': {'value': request.POST.get('end_date', '')}
        },
        'schedule_versions': schedule_versions
    }
    
    return render(request, 'schedule/schedule_generator.html', context)

@login_required
@manager_required
def restore_schedule_version(request, version_id):
    logger.info(f"Schedule version restoration requested by {request.user.email} for version {version_id}")
    
    try:
        version = get_object_or_404(ScheduleVersion, id=version_id)
        start_date = version.start_date
        end_date = version.end_date
        
        Schedule.objects.filter(date__gte=version.start_date, date__lte=version.end_date).delete()
        logger.info(f"Deleted existing schedule for period {version.start_date} to {version.end_date}")
        
        restored_count = 0
        for entry in version.entries.all():
            Schedule.objects.create(
                employee=entry.employee,
                equipment=entry.equipment,
                date=entry.date,
                shift_type=entry.shift_type
            )
            restored_count += 1
        
        logger.info(f"Restored {restored_count} schedule entries from version {version.name}")
        messages.success(request, f"Расписание успешно восстановлено из версии {version.name}")
    except Exception as e:
        logger.error(f"Failed to restore schedule version: {str(e)}")
        messages.error(request, f"Не удалось восстановить расписание: {str(e)}")
    
    return redirect('manager_schedule')

def find_maximum_weighted_matching(employee_nodes, shift_nodes, edges):
    import heapq
    
    matching = {}           # shift_node -> employee_id
    reverse_matching = {}   # employee_id -> set of shift_nodes
    
    shifts_by_date = {}
    shifts_by_date_equipment = {}
    
    for shift_node in shift_nodes:
        date, equipment_id, shift_type = shift_node
        
        if date not in shifts_by_date:
            shifts_by_date[date] = []
        shifts_by_date[date].append(shift_node)
        
        if date not in shifts_by_date_equipment:
            shifts_by_date_equipment[date] = {}
        if equipment_id not in shifts_by_date_equipment[date]:
            shifts_by_date_equipment[date][equipment_id] = []
        shifts_by_date_equipment[date][equipment_id].append(shift_node)
    
    valid_edges = {}
    for employee_id in employee_nodes:
        employee = Employee.objects.get(id=employee_id)
        
        if not EmployeeEquipmentSkill.objects.filter(employee=employee).exists():
            continue
            
        for shift_node in shift_nodes:
            date, equipment_id, shift_type = shift_node
            is_weekend = date.weekday() >= 5
            
            skill = EmployeeEquipmentSkill.objects.filter(
                employee=employee,
                equipment_id=equipment_id
            ).first()
            
            if not skill:
                continue
            
            if employee.shift_availability == 'morning_only' and shift_type != 'morning':
                continue
                
            if employee.shift_availability == 'day_only' and shift_type == 'night':
                continue
                
            if employee.shift_availability == 'all_shifts' and not is_weekend and shift_type == 'morning':
                continue
                
            time_off = TimeOffRequest.objects.filter(
                employee=employee,
                start_date__lte=date,
                end_date__gte=date,
                status='approved'
            ).exists()
            
            if time_off:
                continue
                
            weight = edges.get((employee_id, shift_node), 0)
            
            if skill.skill_level == 'primary':
                weight += 5000
            else:
                continue
            
            current_date_month = date.month
            current_date_year = date.year
            working_days = get_working_days_in_month(current_date_year, current_date_month)
            
            required_hours = working_days * 6
            if float(employee.rate) == 1.5:
                required_hours = round(required_hours * 1.5)
            
            current_hours = 0
            for s in Schedule.objects.filter(
                employee=employee,
                date__month=current_date_month,
                date__year=current_date_year
            ):
                if s.shift_type == 'morning':
                    current_hours += 6
                elif s.shift_type == 'evening':
                    current_hours += 6
                elif s.shift_type == 'night':
                    current_hours += 12
            
            future_hours = 0
            if employee_id in reverse_matching:
                for s_node in reverse_matching[employee_id]:
                    if s_node[0].month == current_date_month and s_node[0].year == current_date_year:
                        if s_node[2] == 'morning':
                            future_hours += 6
                        elif s_node[2] == 'evening':
                            future_hours += 6
                        elif s_node[2] == 'night':
                            future_hours += 12
            
            shift_hours = 12 if shift_type == 'night' else 6
            total_hours = current_hours + future_hours + shift_hours
            
            if total_hours > required_hours + 12:
                weight -= (total_hours - required_hours) * 200
            elif total_hours > required_hours + 6:
                weight -= (total_hours - required_hours) * 100
            elif total_hours > required_hours:
                weight -= (total_hours - required_hours) * 50
            elif total_hours == required_hours:
                weight += 2000
            elif total_hours >= required_hours - 6:
                weight += 1500
            elif total_hours >= required_hours - 12:
                weight += 1000
            else:
                weight += 500
            
            has_night_conflict = False
            for days_back in range(1, 4):
                prev_day = date - timedelta(days=days_back)
                prev_night_shift = Schedule.objects.filter(
                    employee=employee,
                    date=prev_day,
                    shift_type='night'
                ).exists()
                
                if prev_night_shift:
                    if days_back < 3:
                        has_night_conflict = True
                        break
                    else:
                        weight -= 500
            
            if has_night_conflict:
                continue
            
            prev_day_schedule = Schedule.objects.filter(
                employee=employee,
                date=date - timedelta(days=1)
            ).exists()
            
            if prev_day_schedule:
                weight -= 300
            
            if is_weekend and employee.shift_availability == 'all_shifts':
                has_worked_recently = False
                for days_back in range(1, 4):
                    prev_day = date - timedelta(days=days_back)
                    prev_shift = Schedule.objects.filter(
                        employee=employee,
                        date=prev_day
                    ).exists()
                    
                    if prev_shift:
                        has_worked_recently = True
                        break
                
                if has_worked_recently:
                    continue
                
                for other_shift in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                    if other_shift in matching and matching[other_shift] == employee_id:
                        weight += 3000
            
            if not is_weekend and employee.shift_availability == 'all_shifts':
                if shift_type == 'evening':
                    night_shift = None
                    for s in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                        if s[2] == 'night':
                            night_shift = s
                            break
                    
                    if night_shift and night_shift in matching and matching[night_shift] == employee_id:
                        weight += 3000
                
                elif shift_type == 'night':
                    evening_shift = None
                    for s in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                        if s[2] == 'evening':
                            evening_shift = s
                            break
                    
                    if evening_shift and evening_shift in matching and matching[evening_shift] == employee_id:
                        weight += 3000
                    else:
                        continue
            
            valid_edges[(employee_id, shift_node)] = weight
    
    def find_max_weight_augmenting_path():
        """
        Find an augmenting path with maximum weight using a modified BFS approach.
        Returns the path as a list of alternating employee_id and shift_node.
        """
        dist = {}
        prev = {}
        visited = set()
        
        queue = []
        
        unmatched_employees = set(employee_nodes) - set(reverse_matching.keys())
        for employee_id in unmatched_employees:
            dist[employee_id] = 0
            queue.append(employee_id)
            visited.add(employee_id)
        
        if not unmatched_employees:
            for employee_id in employee_nodes:
                if employee_id in reverse_matching:
                    dist[employee_id] = 0
                    queue.append(employee_id)
                    visited.add(employee_id)
        
        found_path = False
        target_shift = None
        
        while queue and not found_path:
            current = queue.pop(0)
            
            if isinstance(current, int):
                for shift_node, weight in [(s, w) for (e, s), w in valid_edges.items() if e == current]:
                    if shift_node in visited:
                        continue
                    
                    if shift_node not in matching:
                        prev[shift_node] = current
                        target_shift = shift_node
                        found_path = True
                        break
                    
                    matched_employee = matching[shift_node]
                    if matched_employee not in visited:
                        dist[matched_employee] = dist[current] + 1
                        prev[shift_node] = current
                        prev[matched_employee] = shift_node
                        visited.add(shift_node)
                        visited.add(matched_employee)
                        queue.append(matched_employee)
        
        if not found_path:
            return None
        
        path = []
        current = target_shift
        while current is not None:
            path.append(current)
            current = prev.get(current)
            
        path.reverse()
        
        return path
    
    iteration = 0
    max_iterations = 100
    
    while iteration < max_iterations:
        iteration += 1
        
        augmenting_path = find_max_weight_augmenting_path()
        
        if augmenting_path is None:
            break
        
        for i in range(0, len(augmenting_path) - 1, 2):
            employee_id = augmenting_path[i]
            shift_node = augmenting_path[i + 1]
            
            if shift_node in matching:
                old_employee_id = matching[shift_node]
                if old_employee_id in reverse_matching:
                    reverse_matching[old_employee_id].remove(shift_node)
                    if not reverse_matching[old_employee_id]:
                        del reverse_matching[old_employee_id]
            
            matching[shift_node] = employee_id
            if employee_id not in reverse_matching:
                reverse_matching[employee_id] = set()
            reverse_matching[employee_id].add(shift_node)
    
    unassigned_shifts = [s for s in shift_nodes if s not in matching]
    
    if unassigned_shifts:
        print(f"Found {len(unassigned_shifts)} unassigned shifts. Attempting to assign with relaxed constraints.")
        
        unassigned_shifts.sort(key=lambda s: (s[0], s[2]))
        
        for shift_node in unassigned_shifts:
            date, equipment_id, shift_type = shift_node
            is_weekend = date.weekday() >= 5
            
            candidates = []
            
            for employee_id in employee_nodes:
                employee = Employee.objects.get(id=employee_id)
                
                if not EmployeeEquipmentSkill.objects.filter(employee=employee).exists():
                    continue
                
                weight = 0
                
                skill = EmployeeEquipmentSkill.objects.filter(
                    employee=employee,
                    equipment_id=equipment_id
                ).first()
                
                if not skill:
                    continue
                
                if skill.skill_level == 'primary':
                    weight += 1000
                else:
                    weight += 100
                
                if employee.shift_availability == 'morning_only' and shift_type != 'morning':
                    continue
                    
                if employee.shift_availability == 'day_only' and shift_type == 'night':
                    continue
                    
                if employee.shift_availability == 'all_shifts' and not is_weekend and shift_type == 'morning':
                    continue
                
                time_off = TimeOffRequest.objects.filter(
                    employee=employee,
                    start_date__lte=date,
                    end_date__gte=date,
                    status='approved'
                ).exists()
                
                if time_off:
                    continue
                
                has_shift_on_date = False
                if employee_id in reverse_matching:
                    for existing_shift in reverse_matching[employee_id]:
                        if existing_shift[0] == date:
                            if is_weekend and employee.shift_availability == 'all_shifts':
                                if existing_shift[1] != equipment_id:
                                    has_shift_on_date = True
                                    break
                            else:
                                has_shift_on_date = True
                                break
                
                if has_shift_on_date:
                    continue
                
                has_night_conflict = False
                if employee_id in reverse_matching:
                    for existing_shift in reverse_matching[employee_id]:
                        existing_date, _, existing_shift_type = existing_shift
                        if existing_shift_type == 'night':
                            days_diff = (date - existing_date).days
                            if days_diff < 3:
                                has_night_conflict = True
                                break
                
                if has_night_conflict:
                    continue
                
                if employee.shift_availability == 'all_shifts':
                    if is_weekend:
                        already_assigned_to_other = False
                        for other_shift in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                            if other_shift in matching and matching[other_shift] != employee_id:
                                already_assigned_to_other = True
                                break
                                
                        if already_assigned_to_other:
                            continue
                            
                        weight += 2000
                    else:
                        if shift_type == 'evening':
                            night_shift = None
                            for s in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                                if s[2] == 'night':
                                    night_shift = s
                                    break
                                    
                            if night_shift and night_shift in matching and matching[night_shift] != employee_id:
                                continue
                                
                        elif shift_type == 'night':
                            evening_shift = None
                            for s in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                                if s[2] == 'evening':
                                    evening_shift = s
                                    break
                                    
                            if evening_shift and evening_shift in matching and matching[evening_shift] != employee_id:
                                continue
                
                heapq.heappush(candidates, (-weight, employee_id))
            
            if candidates:
                _, best_employee_id = heapq.heappop(candidates)
                matching[shift_node] = best_employee_id
                if best_employee_id not in reverse_matching:
                    reverse_matching[best_employee_id] = set()
                reverse_matching[best_employee_id].add(shift_node)
                
                employee = Employee.objects.get(id=best_employee_id)
                if is_weekend and employee.shift_availability == 'all_shifts':
                    for other_shift in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                        if other_shift != shift_node and other_shift not in matching:
                            matching[other_shift] = best_employee_id
                            reverse_matching[best_employee_id].add(other_shift)
                
                if not is_weekend and employee.shift_availability == 'all_shifts':
                    if shift_type == 'evening':
                        for other_shift in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                            if other_shift[2] == 'night' and other_shift not in matching:
                                matching[other_shift] = best_employee_id
                                reverse_matching[best_employee_id].add(other_shift)
                    elif shift_type == 'night':
                        for other_shift in shifts_by_date_equipment.get(date, {}).get(equipment_id, []):
                            if other_shift[2] == 'evening' and other_shift not in matching:
                                matching[other_shift] = best_employee_id
                                reverse_matching[best_employee_id].add(other_shift)
    
    try:
        for date in shifts_by_date_equipment:
            is_weekend = date.weekday() >= 5
            if is_weekend:
                for equipment_id, shifts in shifts_by_date_equipment[date].items():
                    if not shifts:
                        continue
                    
                    assigned_workers = set()
                    for shift in shifts:
                        if shift in matching:
                            worker_id = matching[shift]
                            try:
                                employee = Employee.objects.get(id=worker_id)
                                if employee.shift_availability == 'all_shifts':
                                    assigned_workers.add(worker_id)
                            except Employee.DoesNotExist:
                                continue
                    
                    if len(assigned_workers) > 1:
                        worker_counts = {w: sum(1 for s in shifts if s in matching and matching[s] == w)
                                        for w in assigned_workers}
                        if worker_counts:
                            best_worker = max(worker_counts.items(), key=lambda x: x[1])[0]
                            
                            for shift in shifts:
                                if shift in matching and matching[shift] in assigned_workers:
                                    old_worker = matching[shift]
                                    if old_worker != best_worker:
                                        if old_worker in reverse_matching:
                                            reverse_matching[old_worker].remove(shift)
                                            if not reverse_matching[old_worker]:
                                                del reverse_matching[old_worker]
                                        
                                        matching[shift] = best_worker
                                        if best_worker not in reverse_matching:
                                            reverse_matching[best_worker] = set()
                                        reverse_matching[best_worker].add(shift)
    except Exception as e:
        print(f"Error in weekend shift handling: {e}")
    
    try:
        for date in shifts_by_date_equipment:
            is_weekend = date.weekday() >= 5
            if not is_weekend:
                for equipment_id, shifts in shifts_by_date_equipment[date].items():
                    evening_shift = None
                    night_shift = None
                    for shift in shifts:
                        if shift[2] == 'evening':
                            evening_shift = shift
                        elif shift[2] == 'night':
                            night_shift = shift
                    
                    if not evening_shift or not night_shift:
                        continue
                    
                    if (evening_shift in matching and night_shift in matching and
                        matching[evening_shift] != matching[night_shift]):
                        
                        evening_worker = matching[evening_shift]
                        night_worker = matching[night_shift]
                        
                        evening_worker_skill = EmployeeEquipmentSkill.objects.filter(
                            employee_id=evening_worker,
                            equipment_id=equipment_id
                        ).first()
                        
                        night_worker_skill = EmployeeEquipmentSkill.objects.filter(
                            employee_id=night_worker,
                            equipment_id=equipment_id
                        ).first()
                        
                        if (evening_worker_skill and evening_worker_skill.skill_level == 'primary'):
                            best_worker = evening_worker
                        elif (night_worker_skill and night_worker_skill.skill_level == 'primary'):
                            best_worker = night_worker
                        else:
                            best_worker = evening_worker
                        
                        for shift in [evening_shift, night_shift]:
                            old_worker = matching[shift]
                            if old_worker != best_worker:
                                if old_worker in reverse_matching:
                                    reverse_matching[old_worker].remove(shift)
                                    if not reverse_matching[old_worker]:
                                        del reverse_matching[old_worker]
                                
                                matching[shift] = best_worker
                                if best_worker not in reverse_matching:
                                    reverse_matching[best_worker] = set()
                                reverse_matching[best_worker].add(shift)
    except Exception as e:
        print(f"Error in evening/night shift handling: {e}")
    
    try:
        for employee_id in employee_nodes:
            try:
                employee = Employee.objects.get(id=employee_id)
                if employee_id not in reverse_matching:
                    continue
                    
                night_shifts = [s for s in reverse_matching[employee_id] if s[2] == 'night']
                if len(night_shifts) <= 1:
                    continue
                    
                night_shifts.sort(key=lambda x: x[0])
                
                violations = []
                for i in range(1, len(night_shifts)):
                    days_between = (night_shifts[i][0] - night_shifts[i-1][0]).days
                    if days_between < 3:
                        violations.append((night_shifts[i-1], night_shifts[i]))
                
                for shift1, shift2 in violations:
                    date, equipment_id, shift_type = shift2
                    candidates = []
                    
                    for other_id in employee_nodes:
                        if other_id == employee_id:
                            continue
                            
                        skill = EmployeeEquipmentSkill.objects.filter(
                            employee_id=other_id,
                            equipment_id=equipment_id
                        ).exists()
                        
                        if not skill:
                            continue
                            
                        has_shift = False
                        if other_id in reverse_matching:
                            for s in reverse_matching[other_id]:
                                if s[0] == date:
                                    has_shift = True
                                    break
                        
                        if has_shift:
                            continue
                            
                        try:
                            other_employee = Employee.objects.get(id=other_id)
                            time_off = TimeOffRequest.objects.filter(
                                employee=other_employee,
                                start_date__lte=date,
                                end_date__gte=date,
                                status='approved'
                            ).exists()
                            
                            if time_off:
                                continue
                                
                            if other_employee.shift_availability == 'morning_only':
                                continue
                                
                            if other_employee.shift_availability == 'day_only':
                                continue
                            
                            candidates.append(other_id)
                        except Employee.DoesNotExist:
                            continue
                    
                    if candidates:
                        candidate_counts = {c: len(reverse_matching.get(c, set())) for c in candidates}
                        best_candidate = min(candidate_counts.items(), key=lambda x: x[1])[0]
                        
                        reverse_matching[employee_id].remove(shift2)
                        
                        matching[shift2] = best_candidate
                        if best_candidate not in reverse_matching:
                            reverse_matching[best_candidate] = set()
                        reverse_matching[best_candidate].add(shift2)
            except Employee.DoesNotExist:
                continue
    except Exception as e:
        print(f"Error in rest period handling: {e}")
    
    try:
        for date in shifts_by_date_equipment:
            is_weekend = date.weekday() >= 5
            if is_weekend:
                weekend_workers = {}
                
                for employee_id in employee_nodes:
                    try:
                        employee = Employee.objects.get(id=employee_id)
                        if employee.shift_availability != 'all_shifts':
                            continue
                            
                        if employee_id not in reverse_matching:
                            continue
                            
                        has_weekend_shift = False
                        for shift in reverse_matching[employee_id]:
                            if shift[0] == date:
                                has_weekend_shift = True
                                break
                                
                        if has_weekend_shift:
                            weekend_workers[employee_id] = []
                            
                            for shift in reverse_matching[employee_id]:
                                if shift[0] == date:
                                    weekend_workers[employee_id].append(shift)
                    except Employee.DoesNotExist:
                        continue
                
                for worker_id, shifts in weekend_workers.items():
                    shift_types = set(shift[2] for shift in shifts)
                    
                    if len(shift_types) < 3:
                        missing_types = set(['morning', 'evening', 'night']) - shift_types
                        
                        for missing_type in missing_types:
                            worker_equipment = set(shift[1] for shift in shifts)
                            
                            for equipment_id in worker_equipment:
                                if equipment_id in shifts_by_date_equipment.get(date, {}):
                                    for shift in shifts_by_date_equipment[date][equipment_id]:
                                        if shift[2] == missing_type and shift in matching:
                                            current_worker = matching[shift]
                                            
                                            if current_worker == worker_id:
                                                continue
                                                
                                            if current_worker in reverse_matching:
                                                reverse_matching[current_worker].remove(shift)
                                                if not reverse_matching[current_worker]:
                                                    del reverse_matching[current_worker]
                                            
                                            matching[shift] = worker_id
                                            reverse_matching[worker_id].add(shift)
                                            break
    except Exception as e:
        print(f"Error in weekend shift pattern handling: {e}")
    
    try:
        for employee_id in employee_nodes:
            try:
                employee = Employee.objects.get(id=employee_id)
                if employee.shift_availability != 'all_shifts' or employee_id not in reverse_matching:
                    continue
                    
                all_shifts = list(reverse_matching[employee_id])
                all_shifts.sort(key=lambda x: x[0])
                
                weekend_shifts = [shift for shift in all_shifts if shift[0].weekday() >= 5]
                
                for weekend_shift in weekend_shifts:
                    weekend_date = weekend_shift[0]
                    
                    for days_after in range(1, 4):
                        next_date = weekend_date + timedelta(days=days_after)
                        
                        next_date_shifts = [shift for shift in all_shifts if shift[0] == next_date]
                        
                        for shift in next_date_shifts:
                            date, equipment_id, shift_type = shift
                            
                            candidates = []
                            for other_id in employee_nodes:
                                if other_id == employee_id:
                                    continue
                                    
                                skill = EmployeeEquipmentSkill.objects.filter(
                                    employee_id=other_id,
                                    equipment_id=equipment_id
                                ).exists()
                                
                                if not skill:
                                    continue
                                    
                                has_shift = False
                                if other_id in reverse_matching:
                                    for s in reverse_matching[other_id]:
                                        if s[0] == date:
                                            has_shift = True
                                            break
                                
                                if has_shift:
                                    continue
                                    
                                try:
                                    other_employee = Employee.objects.get(id=other_id)
                                    time_off = TimeOffRequest.objects.filter(
                                        employee=other_employee,
                                        start_date__lte=date,
                                        end_date__gte=date,
                                        status='approved'
                                    ).exists()
                                    
                                    if time_off:
                                        continue
                                        
                                    if shift_type == 'morning' and other_employee.shift_availability not in ['morning_only', 'day_only', 'all_shifts']:
                                        continue
                                        
                                    if shift_type in ['evening', 'night'] and other_employee.shift_availability not in ['day_only', 'all_shifts']:
                                        continue
                                        
                                    if shift_type == 'night' and other_employee.shift_availability == 'day_only':
                                        continue
                                    
                                    candidates.append(other_id)
                                except Employee.DoesNotExist:
                                    continue
                            
                            if candidates:
                                candidate_counts = {c: len(reverse_matching.get(c, set())) for c in candidates}
                                best_candidate = min(candidate_counts.items(), key=lambda x: x[1])[0]
                                
                                reverse_matching[employee_id].remove(shift)
                                
                                matching[shift] = best_candidate
                                if best_candidate not in reverse_matching:
                                    reverse_matching[best_candidate] = set()
                                reverse_matching[best_candidate].add(shift)
            except Employee.DoesNotExist:
                continue
    except Exception as e:
        print(f"Error in rest days handling: {e}")
    
    try:
        for employee_id in employee_nodes:
            try:
                primary_skills = EmployeeEquipmentSkill.objects.filter(
                    employee_id=employee_id,
                    skill_level='primary'
                )
                
                if not primary_skills.exists() or employee_id not in reverse_matching:
                    continue
                    
                primary_equipment_ids = [skill.equipment_id for skill in primary_skills]
                
                employee_shifts = list(reverse_matching[employee_id])
                
                non_primary_shifts = [shift for shift in employee_shifts if shift[1] not in primary_equipment_ids]
                
                for shift in non_primary_shifts:
                    date, equipment_id, shift_type = shift
                    
                    primary_skilled_employees = EmployeeEquipmentSkill.objects.filter(
                        equipment_id=equipment_id,
                        skill_level='primary'
                    ).values_list('employee_id', flat=True)
                    
                    candidates = []
                    for other_id in primary_skilled_employees:
                        if other_id == employee_id:
                            continue
                            
                        has_shift = False
                        if other_id in reverse_matching:
                            for s in reverse_matching[other_id]:
                                if s[0] == date:
                                    has_shift = True
                                    break
                        
                        if has_shift:
                            continue
                            
                            try:
                                other_employee = Employee.objects.get(id=other_id)
                                time_off = TimeOffRequest.objects.filter(
                                    employee=other_employee,
                                    start_date__lte=date,
                                    end_date__gte=date,
                                    status='approved'
                                ).exists()
                                
                                if time_off:
                                    continue
                                    
                                if shift_type == 'morning' and other_employee.shift_availability not in ['morning_only', 'day_only', 'all_shifts']:
                                    continue
                                    
                                if shift_type in ['evening', 'night'] and other_employee.shift_availability not in ['day_only', 'all_shifts']:
                                    continue
                                    
                                if shift_type == 'night' and other_employee.shift_availability == 'day_only':
                                    continue
                                
                                candidates.append(other_id)
                            except Employee.DoesNotExist:
                                continue
                    
                    if candidates:
                        candidate_counts = {c: len(reverse_matching.get(c, set())) for c in candidates}
                        best_candidate = min(candidate_counts.items(), key=lambda x: x[1])[0]
                        
                        reverse_matching[employee_id].remove(shift)
                        
                        matching[shift] = best_candidate
                        if best_candidate not in reverse_matching:
                            reverse_matching[best_candidate] = set()
                        reverse_matching[best_candidate].add(shift)
            except Exception as e:
                print(f"Error processing employee {employee_id}: {e}")
                continue
    except Exception as e:
        print(f"Error in primary equipment assignment: {e}")
    
    final_unassigned = [s for s in shift_nodes if s not in matching]
    if final_unassigned:
        print(f"WARNING: Still have {len(final_unassigned)} unassigned shifts after post-processing.")
        
        for shift_node in final_unassigned:
            employee_counts = {e_id: len(reverse_matching.get(e_id, set())) for e_id in employee_nodes}
            best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
            
            matching[shift_node] = best_employee_id
            if best_employee_id not in reverse_matching:
                reverse_matching[best_employee_id] = set()
            reverse_matching[best_employee_id].add(shift_node)
    
    result = [(employee_id, shift_node) for shift_node, employee_id in matching.items()]
    return result

def apply_scheduling_rules(initial_matching, employee_nodes, shift_nodes, edges, day_workers, on_call_workers):
    import heapq
    
    matching_dict = {}
    for employee_id, shift_node in initial_matching:
        matching_dict[shift_node] = employee_id
    
    shifts_by_date = {}
    for shift_node in shift_nodes:
        date, equipment_id, shift_type = shift_node
        if date not in shifts_by_date:
            shifts_by_date[date] = []
        shifts_by_date[date].append(shift_node)
    
    shifts_by_date_equipment = {}
    for date, date_shifts in shifts_by_date.items():
        shifts_by_date_equipment[date] = {}
        for shift in date_shifts:
            _, equipment_id, _ = shift
            if equipment_id not in shifts_by_date_equipment[date]:
                shifts_by_date_equipment[date][equipment_id] = []
            shifts_by_date_equipment[date][equipment_id].append(shift)
    
    employee_workload = {employee_id: 0 for employee_id in employee_nodes}
    employee_hours = {employee_id: 0 for employee_id in employee_nodes}
    employee_required_hours = {}
    
    for employee_id in employee_nodes:
        employee = Employee.objects.get(id=employee_id)
        first_date = min([shift[0] for shift in shift_nodes]) if shift_nodes else datetime.now().date()
        working_days = get_working_days_in_month(first_date.year, first_date.month)
        required_hours = working_days * 6 
        if float(employee.rate) == 1.5:
            required_hours = round(required_hours * 1.5)
        employee_required_hours[employee_id] = required_hours
    
    for shift_node, employee_id in matching_dict.items():
        employee_workload[employee_id] += 1
        _, _, shift_type = shift_node
        if shift_type == 'morning':
            employee_hours[employee_id] += 6
        elif shift_type == 'evening':
            employee_hours[employee_id] += 6
        elif shift_type == 'night':
            employee_hours[employee_id] += 12
    
    for date, date_shifts in shifts_by_date.items():
        is_weekend = date.weekday() >= 5
        
        if not is_weekend:
            morning_shifts = [shift for shift in date_shifts if shift[2] == 'morning']
            
            for shift in morning_shifts:
                if shift in matching_dict and matching_dict[shift] in [worker.id for worker in day_workers]:
                    continue
                
                candidates = []
                for worker in day_workers:
                    if (worker.id, shift) in edges:
                        time_off = TimeOffRequest.objects.filter(
                            employee=worker,
                            start_date__lte=shift[0],
                            end_date__gte=shift[0],
                            status='approved'
                        ).exists()
                        
                        if time_off:
                            continue
                        
                        has_shift_on_date = False
                        for s, e_id in matching_dict.items():
                            if e_id == worker.id and s[0] == shift[0]:
                                has_shift_on_date = True
                                break
                        
                        if has_shift_on_date:
                            continue
                        
                        weight = edges[(worker.id, shift)]
                        
                        hours_if_assigned = employee_hours[worker.id] + 6
                        hours_diff = abs(hours_if_assigned - employee_required_hours[worker.id])
                        adjusted_weight = weight - (hours_diff * 2)
                        
                        time_off = TimeOffRequest.objects.filter(
                            employee=worker,
                            start_date__lte=shift[0],
                            end_date__gte=shift[0]
                        ).first()
                        
                        if time_off and time_off.status == 'pending':
                            if time_off.priority == 'high':
                                adjusted_weight -= 100
                            elif time_off.priority == 'medium':
                                adjusted_weight -= 50
                            elif time_off.priority == 'low':
                                adjusted_weight -= 20
                        
                        prev_day = shift[0] - timedelta(days=1)
                        prev_day_schedule = Schedule.objects.filter(
                            employee=worker,
                            date=prev_day
                        ).exists()
                        
                        if prev_day_schedule:
                            adjusted_weight -= 80
                        
                        heapq.heappush(candidates, (-adjusted_weight, worker.id))
                
                if candidates:
                    _, best_worker_id = heapq.heappop(candidates)
                    
                    if shift in matching_dict:
                        old_employee_id = matching_dict[shift]
                        employee_workload[old_employee_id] -= 1
                        employee_hours[old_employee_id] -= 6 
                    
                    matching_dict[shift] = best_worker_id
                    employee_workload[best_worker_id] += 1
                    employee_hours[best_worker_id] += 6
    
    for shift_node in shift_nodes:
        date, equipment_id, shift_type = shift_node
        if date.weekday() < 5 and shift_type in ['evening', 'night'] and shift_node in matching_dict:
            old_employee_id = matching_dict[shift_node]
            employee_workload[old_employee_id] -= 1
            shift_hours = 12 if shift_type == 'night' else 6
            employee_hours[old_employee_id] -= shift_hours
            del matching_dict[shift_node]
    
    weekday_assignments = {} 
    
    weekday_dates = [date for date in shifts_by_date.keys() if date.weekday() < 5]
    weekday_dates.sort()
    
    for date in weekday_dates:
        if date not in weekday_assignments:
            weekday_assignments[date] = set()
            
        equipment_shifts = shifts_by_date_equipment.get(date, {})
        
        for equipment_id, shifts in equipment_shifts.items():
            evening_shift = None
            night_shift = None
            
            for shift in shifts:
                if shift[2] == 'evening':
                    evening_shift = shift
                elif shift[2] == 'night':
                    night_shift = shift
            
            if evening_shift and night_shift:
                candidates = []
                for worker in on_call_workers:
                    if worker.id in weekday_assignments.get(date, set()):
                        continue
                        
                    approved_time_off = TimeOffRequest.objects.filter(
                        employee=worker,
                        start_date__lte=date,
                        end_date__gte=date,
                        status='approved'
                    ).exists()
                    
                    high_priority_time_off = TimeOffRequest.objects.filter(
                        employee=worker,
                        start_date__lte=date,
                        end_date__gte=date,
                        status='pending',
                        priority='high'
                    ).exists()
                    
                    if approved_time_off or high_priority_time_off:
                        continue
                    
                    skill = EmployeeEquipmentSkill.objects.filter(
                        employee=worker,
                        equipment_id=equipment_id
                    ).exists()
                    
                    if not skill:
                        continue
                    
                    prev_day = date - timedelta(days=1)
                    if prev_day in weekday_assignments and worker.id in weekday_assignments[prev_day]:
                        continue
                    
                    next_day = date + timedelta(days=1)
                    if next_day in weekday_assignments and worker.id in weekday_assignments[next_day]:
                        continue
                    
                    has_recent_night_shift = False
                    for days_back in range(1, 4):
                        prev_day = date - timedelta(days=days_back)
                        prev_night_shift = Schedule.objects.filter(
                            employee=worker,
                            date=prev_day,
                            shift_type='night'
                        ).exists()
                        
                        if prev_night_shift and days_back < 3:
                            has_recent_night_shift = True
                            break
                    
                    if has_recent_night_shift:
                        continue
                    
                    if (worker.id, evening_shift) not in edges or (worker.id, night_shift) not in edges:
                        continue
                        
                    total_weight = edges[(worker.id, evening_shift)] + edges[(worker.id, night_shift)]
                    
                    total_hours = employee_hours[worker.id] + 18
                    
                    hours_diff = abs(total_hours - employee_required_hours[worker.id])
                    adjusted_weight = total_weight - (hours_diff * 2)
                    
                    time_off = TimeOffRequest.objects.filter(
                        employee=worker,
                        start_date__lte=date,
                        end_date__gte=date,
                        status='pending'
                    ).first()
                    
                    if time_off:
                        if time_off.priority == 'high':
                            continue
                        elif time_off.priority == 'medium':
                            adjusted_weight -= 500 
                        elif time_off.priority == 'low':
                            adjusted_weight -= 200
                    
                    heapq.heappush(candidates, (-adjusted_weight, worker.id))
                
                if candidates:
                    _, best_worker_id = heapq.heappop(candidates)
                    
                    weekday_assignments[date].add(best_worker_id)
                    
                    for shift in [evening_shift, night_shift]:
                        matching_dict[shift] = best_worker_id
                        employee_workload[best_worker_id] += 1
                        new_shift_hours = 12 if shift[2] == 'night' else 6
                        employee_hours[best_worker_id] += new_shift_hours
                    
                    print(f"Assigned worker {best_worker_id} to evening+night shifts on {date} for equipment {equipment_id}")
                else:
                    print(f"Warning: No suitable worker found for evening+night shifts on {date} for equipment {equipment_id}")
                    
                    fallback_candidates = []
                    for worker in on_call_workers:
                        if (worker.id, evening_shift) in edges and (worker.id, night_shift) in edges:
                            approved_time_off = TimeOffRequest.objects.filter(
                                employee=worker,
                                start_date__lte=date,
                                end_date__gte=date,
                                status='approved'
                            ).exists()
                            
                            high_priority_time_off = TimeOffRequest.objects.filter(
                                employee=worker,
                                start_date__lte=date,
                                end_date__gte=date,
                                status='pending',
                                priority='high'
                            ).exists()
                            
                            if not (approved_time_off or high_priority_time_off):
                                fallback_candidates.append(worker.id)
                    
                    if fallback_candidates:
                        best_worker_id = min(fallback_candidates, key=lambda w_id: employee_workload[w_id])
                        
                        weekday_assignments[date].add(best_worker_id)
                        
                        for shift in [evening_shift, night_shift]:
                            matching_dict[shift] = best_worker_id
                            employee_workload[best_worker_id] += 1
                            new_shift_hours = 12 if shift[2] == 'night' else 6
                            employee_hours[best_worker_id] += new_shift_hours
                        
                        print(f"Assigned fallback worker {best_worker_id} to evening+night shifts on {date}")
                
                for shift in shifts:
                    if (shift[2] in ['evening', 'night'] and
                        shift != evening_shift and shift != night_shift and
                        (shift not in matching_dict or
                         matching_dict[shift] not in [worker.id for worker in on_call_workers])):
                        
                        candidates = []
                        for worker in on_call_workers:
                            if (worker.id, shift) in edges:
                                approved_time_off = TimeOffRequest.objects.filter(
                                    employee=worker,
                                    start_date__lte=shift[0],
                                    end_date__gte=shift[0],
                                    status='approved'
                                ).exists()
                                
                                high_priority_time_off = TimeOffRequest.objects.filter(
                                    employee=worker,
                                    start_date__lte=shift[0],
                                    end_date__gte=shift[0],
                                    status='pending',
                                    priority='high'
                                ).exists()
                                
                                if approved_time_off or high_priority_time_off:
                                    continue
                                
                                has_shift_on_date = False
                                for s, e_id in matching_dict.items():
                                    if e_id == worker.id and s[0] == shift[0]:
                                        has_shift_on_date = True
                                        break
                                
                                if has_shift_on_date:
                                    continue
                                
                                weight = edges[(worker.id, shift)]
                                
                                shift_hours = 12 if shift[2] == 'night' else 6
                                hours_if_assigned = employee_hours[worker.id] + shift_hours
                                hours_diff = abs(hours_if_assigned - employee_required_hours[worker.id])
                                adjusted_weight = weight - (hours_diff * 2)
                                
                                time_off = TimeOffRequest.objects.filter(
                                    employee=worker,
                                    start_date__lte=shift[0],
                                    end_date__gte=shift[0],
                                    status='pending'
                                ).first()
                                
                                if time_off:
                                    if time_off.priority == 'high':
                                        continue
                                    elif time_off.priority == 'medium':
                                        adjusted_weight -= 500
                                    elif time_off.priority == 'low':
                                        adjusted_weight -= 200
                                
                                prev_day = shift[0] - timedelta(days=1)
                                prev_day_schedule = Schedule.objects.filter(
                                    employee=worker,
                                    date=prev_day
                                ).exists()
                                
                                if prev_day_schedule:
                                    adjusted_weight -= 80
                                
                                if shift[2] == 'night':
                                    prev_night_shifts = Schedule.objects.filter(
                                        employee=worker,
                                        shift_type='night',
                                        date__lt=shift[0]
                                    ).order_by('-date')
                                    
                                    if prev_night_shifts.exists():
                                        last_night_shift = prev_night_shifts.first()
                                        days_since_last_night = (shift[0] - last_night_shift.date).days
                                        
                                        if days_since_last_night < 3:
                                            continue
                                
                                heapq.heappush(candidates, (-adjusted_weight, worker.id))
                        
                        if candidates:
                            _, best_worker_id = heapq.heappop(candidates)
                            
                            if shift in matching_dict:
                                old_employee_id = matching_dict[shift]
                                employee_workload[old_employee_id] -= 1
                                old_shift_hours = 12 if shift[2] == 'night' else 6
                                employee_hours[old_employee_id] -= old_shift_hours
                            
                            matching_dict[shift] = best_worker_id
                            employee_workload[best_worker_id] += 1
                            new_shift_hours = 12 if shift[2] == 'night' else 6
                            employee_hours[best_worker_id] += new_shift_hours
    
    for shift_node in shift_nodes:
        date, equipment_id, _ = shift_node
        if date.weekday() >= 5:
            try:
                equipment = Equipment.objects.get(id=equipment_id)
                if equipment.equipment_type == 'rkt_ge' and shift_node in matching_dict:
                    old_employee_id = matching_dict[shift_node]
                    employee_workload[old_employee_id] -= 1
                    shift_hours = 12 if shift_node[2] == 'night' else 6
                    employee_hours[old_employee_id] -= shift_hours
                    del matching_dict[shift_node]
            except Exception as e:
                print(f"Error removing weekend RKT assignment: {e}")
    
    weekend_dates = [date for date in shifts_by_date.keys() if date.weekday() >= 5]
    weekend_dates.sort()
    
    weekend_rkt_workers = {}
    
    for date in weekend_dates:
        rkt_shifts_by_equipment = {}
        for equipment_id, shifts in shifts_by_date_equipment.get(date, {}).items():
            try:
                equipment = Equipment.objects.get(id=equipment_id)
                if equipment.equipment_type == 'rkt_ge':
                    rkt_shifts_by_equipment[equipment_id] = shifts
            except Exception as e:
                print(f"Error processing equipment {equipment_id}: {e}")
        
        if not rkt_shifts_by_equipment:
            continue
        
        for equipment_id, shifts in rkt_shifts_by_equipment.items():
            shift_types = [shift[2] for shift in shifts]
            if len(set(shift_types)) < 3:
                print(f"Warning: Not all shift types present for RKT equipment {equipment_id} on {date}")
                continue
            
            candidates = []
            for worker in on_call_workers:
                already_assigned_weekend = False
                for w_date, w_id in weekend_rkt_workers.items():
                    if w_id == worker.id and w_date != date:
                        already_assigned_weekend = True
                        break
                
                if already_assigned_weekend:
                    continue
                
                approved_time_off = TimeOffRequest.objects.filter(
                    employee=worker,
                    start_date__lte=date,
                    end_date__gte=date,
                    status='approved'
                ).exists()
                
                high_priority_time_off = TimeOffRequest.objects.filter(
                    employee=worker,
                    start_date__lte=date,
                    end_date__gte=date,
                    status='pending',
                    priority='high'
                ).exists()
                
                if approved_time_off or high_priority_time_off:
                    continue
                
                skill = EmployeeEquipmentSkill.objects.filter(
                    employee=worker,
                    equipment_id=equipment_id
                ).exists()
                
                if not skill:
                    continue
                
                total_weight = 0
                total_hours = employee_hours[worker.id]
                can_take_all = True
                
                for shift in shifts:
                    if (worker.id, shift) in edges:
                        total_weight += edges[(worker.id, shift)]
                        if shift[2] == 'morning':
                            total_hours += 6
                        elif shift[2] == 'evening':
                            total_hours += 6
                        elif shift[2] == 'night':
                            total_hours += 12
                    else:
                        can_take_all = False
                        break
                
                if not can_take_all:
                    continue
                
                hours_diff = abs(total_hours - employee_required_hours[worker.id])
                adjusted_weight = total_weight - (hours_diff * 2)
                
                heapq.heappush(candidates, (-adjusted_weight, worker.id))
            
            if candidates:
                _, best_worker_id = heapq.heappop(candidates)
                
                weekend_rkt_workers[date] = best_worker_id
                
                for shift in shifts:
                    matching_dict[shift] = best_worker_id
                    employee_workload[best_worker_id] += 1
                    shift_hours = 12 if shift[2] == 'night' else 6
                    employee_hours[best_worker_id] += shift_hours
                    
                print(f"Assigned worker {best_worker_id} to all RKT shifts on {date} for equipment {equipment_id}")
            else:
                print(f"Warning: No suitable worker found for RKT equipment {equipment_id} on {date}")
                
                least_busy_worker = min(on_call_workers, key=lambda w: employee_workload[w.id])
                
                for shift in shifts:
                    if shift in matching_dict:
                        old_employee_id = matching_dict[shift]
                        employee_workload[old_employee_id] -= 1
                        old_shift_hours = 12 if shift[2] == 'night' else 6
                        employee_hours[old_employee_id] -= old_shift_hours
                    
                    matching_dict[shift] = least_busy_worker.id
                    employee_workload[least_busy_worker.id] += 1
                    new_shift_hours = 12 if shift[2] == 'night' else 6
                    employee_hours[least_busy_worker.id] += new_shift_hours
                
                print(f"Assigned least busy worker {least_busy_worker.id} to all RKT shifts on {date}")
            
            for equipment_id, shifts in equipment_shifts.items():
                equipment = Equipment.objects.get(id=equipment_id)
                
                if equipment.equipment_type == 'rkt_ge':
                    continue
                
                if equipment.equipment_type != 'rkt_ge' and any(s[2] != 'morning' for s in shifts):
                    continue
                
                equipment_shifts = [s for s in shifts if s[0] == date and s[1] == equipment_id]
                
                all_assigned = all(shift in matching_dict for shift in equipment_shifts)
                
                if not all_assigned:
                    continue
                
                assigned_workers = set()
                for shift in equipment_shifts:
                    worker_id = matching_dict[shift]
                    if worker_id in [w.id for w in on_call_workers]:
                        assigned_workers.add(worker_id)
                
                if len(assigned_workers) == 1:
                    continue
                
                candidates = []
                for worker in on_call_workers:
                    total_weight = 0
                    all_shifts_available = True
                    
                    approved_time_off = TimeOffRequest.objects.filter(
                        employee=worker,
                        start_date__lte=date,
                        end_date__gte=date,
                        status='approved'
                    ).exists()
                    
                    high_priority_time_off = TimeOffRequest.objects.filter(
                        employee=worker,
                        start_date__lte=date,
                        end_date__gte=date,
                        status='pending',
                        priority='high'
                    ).exists()
                    
                    if approved_time_off or high_priority_time_off:
                        continue
                        
                    skill = EmployeeEquipmentSkill.objects.filter(
                        employee=worker,
                        equipment=equipment
                    ).exists()
                    
                    if not skill:
                        continue
                    
                    prev_day = date - timedelta(days=1)
                    prev_day_schedule = Schedule.objects.filter(
                        employee=worker,
                        date=prev_day
                    ).exists()
                    
                    if prev_day_schedule:
                        continue 
                    
                    for days_back in range(1, 4):
                        prev_day = date - timedelta(days=days_back)
                        prev_night_shift = Schedule.objects.filter(
                            employee=worker,
                            date=prev_day,
                            shift_type='night'
                        ).exists()
                        
                        if prev_night_shift:
                            all_shifts_available = False
                            break
                    
                    if not all_shifts_available:
                        continue
                    
                    total_hours = employee_hours[worker.id]
                    for shift in shifts:
                        if (worker.id, shift) in edges:
                            total_weight += edges[(worker.id, shift)]
                            if shift[2] == 'morning':
                                total_hours += 6
                            elif shift[2] == 'evening':
                                total_hours += 6
                            elif shift[2] == 'night':
                                total_hours += 12
                        else:
                            all_shifts_available = False
                            break
                    
                    if all_shifts_available:
                        hours_diff = abs(total_hours - employee_required_hours[worker.id])
                        adjusted_weight = total_weight - (hours_diff * 2)
                        
                        heapq.heappush(candidates, (-adjusted_weight, worker.id))
                
                if candidates:
                    _, best_worker_id = heapq.heappop(candidates)
                    
                    for shift in shifts:
                        if shift in matching_dict:
                            old_employee_id = matching_dict[shift]
                            employee_workload[old_employee_id] -= 1
                            old_shift_hours = 12 if shift[2] == 'night' else 6
                            employee_hours[old_employee_id] -= old_shift_hours
                        
                        matching_dict[shift] = best_worker_id
                        employee_workload[best_worker_id] += 1
                        new_shift_hours = 12 if shift[2] == 'night' else 6
                        employee_hours[best_worker_id] += new_shift_hours
    
    for employee_id in employee_nodes:
        if abs(employee_hours[employee_id] - employee_required_hours[employee_id]) <= 6:
            continue
        
        is_overloaded = employee_hours[employee_id] > employee_required_hours[employee_id] + 12
        is_underloaded = employee_hours[employee_id] < employee_required_hours[employee_id] - 12
        
        if is_overloaded:
            employee_shifts = []
            for shift, e_id in matching_dict.items():
                if e_id == employee_id:
                    employee_shifts.append(shift)
            
            employee_shifts.sort(key=lambda x: x[0], reverse=True)
            
            for shift in employee_shifts:
                if employee_hours[employee_id] <= employee_required_hours[employee_id] + 6:
                    break
                
                date, equipment_id, shift_type = shift
                is_weekend = date.weekday() >= 5
                
                if is_weekend and employee_id in [w.id for w in on_call_workers]:
                    continue
                
                if shift_type == 'morning' and employee_id in [w.id for w in day_workers]:
                    continue
                
                candidates = []
                for other_id in employee_nodes:
                    if other_id == employee_id:
                        continue
                    
                    if employee_hours[other_id] >= employee_required_hours[other_id]:
                        continue
                    
                    if (other_id, shift) in edges:
                        time_off = TimeOffRequest.objects.filter(
                            employee=Employee.objects.get(id=other_id),
                            start_date__lte=shift[0],
                            end_date__gte=shift[0],
                            status='approved'
                        ).exists()
                        
                        if time_off:
                            continue
                        
                        conflict = False
                        for other_shift, e_id in matching_dict.items():
                            if e_id == other_id and other_shift[0] == date:
                                conflict = True
                                break
                        
                        if conflict:
                            continue
                        
                        employee = Employee.objects.get(id=other_id)
                        if not ((shift_type == 'morning' and employee.shift_availability == 'morning_only') or
                               (shift_type != 'night' and employee.shift_availability == 'day_only') or
                               employee.shift_availability == 'all_shifts'):
                            continue
                        
                        weight = edges[(other_id, shift)]
                        
                        shift_hours = 12 if shift_type == 'night' else 6
                        hours_if_assigned = employee_hours[other_id] + shift_hours
                        hours_diff = abs(hours_if_assigned - employee_required_hours[other_id])
                        adjusted_weight = weight - (hours_diff * 2)
                        
                        heapq.heappush(candidates, (-adjusted_weight, other_id))
                
                if candidates:
                    _, best_employee_id = heapq.heappop(candidates)
                    
                    matching_dict[shift] = best_employee_id
                    
                    shift_hours = 12 if shift_type == 'night' else 6
                    employee_hours[employee_id] -= shift_hours
                    employee_hours[best_employee_id] += shift_hours
                    
                    employee_workload[employee_id] -= 1
                    employee_workload[best_employee_id] += 1
    
    all_shifts_assigned = True
    for shift_node in shift_nodes:
        if shift_node not in matching_dict:
            all_shifts_assigned = False
            print(f"WARNING: Shift {shift_node} is not assigned in apply_scheduling_rules")
            
            date, equipment_id, shift_type = shift_node
            candidates = []
            
            for employee_id in employee_nodes:
                if (employee_id, shift_node) in edges:
                    weight = edges[(employee_id, shift_node)]
                    
                    has_shift_on_date = False
                    for other_shift, other_employee in matching_dict.items():
                        if other_employee == employee_id and other_shift[0] == date:
                            has_shift_on_date = True
                            break
                    
                    if has_shift_on_date:
                        weight -= 1000
                    
                    heapq.heappush(candidates, (-weight, employee_id))
            
            if candidates:
                _, best_employee_id = heapq.heappop(candidates)
                matching_dict[shift_node] = best_employee_id
                employee_workload[best_employee_id] += 1
                shift_hours = 12 if shift_type == 'night' else 6
                employee_hours[best_employee_id] += shift_hours
            else:
                employee_counts = {e_id: employee_workload[e_id] for e_id in employee_nodes}
                best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
                
                matching_dict[shift_node] = best_employee_id
                employee_workload[best_employee_id] += 1
                shift_hours = 12 if shift_type == 'night' else 6
                employee_hours[best_employee_id] += shift_hours
    
    if not all_shifts_assigned:
        print("WARNING: Some shifts were not assigned during rule application. Emergency assignments were made.")
    
    final_matching = [(employee_id, shift) for shift, employee_id in matching_dict.items()]
    return final_matching

@login_required
def time_off_requests(request):
    status_filter = request.GET.get('status', 'all')
    
    if is_manager(request.user):
        requests = TimeOffRequest.objects.all()
    else:
        requests = TimeOffRequest.objects.filter(employee=request.user.employee)
    
    if status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    pending_requests = requests.filter(status='pending').order_by('-created_at')
    other_requests = requests.exclude(status='pending').order_by('-created_at')
    requests = list(pending_requests) + list(other_requests)
    
    context = {
        'requests': requests,
        'status_filter': status_filter,
        'is_manager': is_manager(request.user)
    }
    
    return render(request, 'time_off/time_off_requests.html', context)

@login_required
def time_off_request_new(request):
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
    time_off_request = get_object_or_404(TimeOffRequest, id=request_id)
    
    if time_off_request.employee.user != request.user:
        messages.error(request, "У вас нет прав для удаления этого запроса.")
        return redirect('time_off_requests')
    
    if time_off_request.status != 'pending':
        messages.error(request, "Можно удалять только запросы со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
    time_off_request.delete()
    messages.success(request, "Запрос на отгул успешно удален.")
    
    return redirect('time_off_requests')

@login_required
@manager_required
@require_POST
def approve_time_off_request(request, request_id):
    time_off_request = get_object_or_404(TimeOffRequest, id=request_id)
    
    if time_off_request.status != 'pending':
        messages.error(request, "Можно одобрять только запросы со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
    time_off_request.status = 'approved'
    time_off_request.manager_comment = request.POST.get('comment', '')
    time_off_request.save()
    
    messages.success(request, "Запрос на отгул успешно одобрен.")
    
    return redirect('time_off_requests')

@login_required
@manager_required
@require_POST
def reject_time_off_request(request, request_id):
    time_off_request = get_object_or_404(TimeOffRequest, id=request_id)
    
    if time_off_request.status != 'pending':
        messages.error(request, "Можно отклонять только запросы со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
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
    
    if time_off_request.status != 'pending':
        messages.error(request, "Можно изменять приоритет только у запросов со статусом 'На рассмотрении'.")
        return redirect('time_off_requests')
    
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
    date = request.POST.get('date')
    employee_id = request.POST.get('employee')
    equipment_id = request.POST.get('equipment')
    shift_type = request.POST.get('shift_type')
    
    logger.info(f"Schedule entry creation requested by {request.user.email} for date {date}")
    
    if not date or not employee_id or not equipment_id or not shift_type:
        messages.error(request, "Пожалуйста, заполните все поля.")
        logger.warning("Schedule entry creation failed: missing fields")
        return redirect('manager_schedule')
    
    try:
        date = datetime.strptime(date, '%Y-%m-%d').date()
        employee = Employee.objects.get(id=employee_id)
        equipment = Equipment.objects.get(id=equipment_id)
        
        skill = EmployeeEquipmentSkill.objects.filter(
            employee=employee,
            equipment=equipment,
            skill_level='primary'
        ).exists()
        
        if not skill:
            messages.error(request, f"Сотрудник {employee.full_name} не имеет основного навыка для работы на аппарате {equipment.name}.")
            logger.warning(f"Schedule entry creation failed: employee {employee.id} doesn't have primary skill for equipment {equipment.id}")
            return redirect('manager_schedule')
        
        if Schedule.objects.filter(employee=employee, date=date).exists():
            messages.error(request, f"Сотрудник {employee.full_name} уже имеет смену на эту дату.")
            logger.warning(f"Schedule entry creation failed: employee {employee.id} already has a shift on {date}")
            return redirect('manager_schedule')
        
        if employee.shift_availability == 'morning_only' and shift_type != 'morning':
            messages.error(request, f"Сотрудник {employee.full_name} может работать только в утреннюю смену.")
            logger.warning(f"Schedule entry creation failed: employee {employee.id} can only work morning shifts")
            return redirect('manager_schedule')
        
        if employee.shift_availability == 'day_only' and shift_type == 'night':
            messages.error(request, f"Сотрудник {employee.full_name} не может работать в ночную смену.")
            logger.warning(f"Schedule entry creation failed: employee {employee.id} cannot work night shifts")
            return redirect('manager_schedule')
        
        time_off = TimeOffRequest.objects.filter(
            employee=employee,
            start_date__lte=date,
            end_date__gte=date,
            status='approved'
        ).exists()
        
        if time_off:
            messages.error(request, f"Сотрудник {employee.full_name} имеет одобренный отгул на эту дату.")
            logger.warning(f"Schedule entry creation failed: employee {employee.id} has approved time off on {date}")
            return redirect('manager_schedule')
        
        Schedule.objects.create(
            employee=employee,
            equipment=equipment,
            shift_type=shift_type,
            date=date
        )
        
        logger.info(f"Schedule entry created for employee {employee.id}, equipment {equipment.id}, date {date}, shift {shift_type}")
        messages.success(request, "Смена успешно добавлена.")
    except (ValueError, Employee.DoesNotExist, Equipment.DoesNotExist) as e:
        messages.error(request, "Произошла ошибка при добавлении смены.")
        logger.error(f"Schedule entry creation failed with error: {str(e)}")
    
    return redirect('manager_schedule')

@login_required
@manager_required
def edit_schedule_entry(request, entry_id):
    logger.info(f"Schedule entry edit requested by {request.user.email} for entry {entry_id}")
    
    entry = get_object_or_404(Schedule, id=entry_id)
    employees = Employee.objects.all()
    equipment_list = Equipment.objects.all()
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        equipment_id = request.POST.get('equipment')
        shift_type = request.POST.get('shift_type')
        
        if not employee_id or not equipment_id or not shift_type:
            messages.error(request, "Пожалуйста, заполните все поля.")
            logger.warning(f"Schedule entry edit failed: missing fields")
            return redirect('edit_schedule_entry', entry_id=entry_id)
        
        try:
            employee = Employee.objects.get(id=employee_id)
            equipment = Equipment.objects.get(id=equipment_id)
            
            skill = EmployeeEquipmentSkill.objects.filter(
                employee=employee,
                equipment=equipment
            ).exists()
            
            if not skill:
                messages.error(request, f"Сотрудник {employee.full_name} не имеет навыка для работы на аппарате {equipment.name}.")
                logger.warning(f"Schedule entry edit failed: employee {employee.id} doesn't have skill for equipment {equipment.id}")
                return redirect('edit_schedule_entry', entry_id=entry_id)
            
            if Schedule.objects.filter(employee=employee, date=entry.date).exclude(id=entry_id).exists():
                messages.error(request, f"Сотрудник {employee.full_name} уже имеет другую смену на эту дату.")
                logger.warning(f"Schedule entry edit failed: employee {employee.id} already has another shift on {entry.date}")
                return redirect('edit_schedule_entry', entry_id=entry_id)
            
            if employee.shift_availability == 'morning_only' and shift_type != 'morning':
                messages.error(request, f"Сотрудник {employee.full_name} может работать только в утреннюю смену.")
                logger.warning(f"Schedule entry edit failed: employee {employee.id} can only work morning shifts")
                return redirect('edit_schedule_entry', entry_id=entry_id)
            
            if employee.shift_availability == 'day_only' and shift_type == 'night':
                messages.error(request, f"Сотрудник {employee.full_name} не может работать в ночную смену.")
                logger.warning(f"Schedule entry edit failed: employee {employee.id} cannot work night shifts")
                return redirect('edit_schedule_entry', entry_id=entry_id)
            
            time_off = TimeOffRequest.objects.filter(
                employee=employee,
                start_date__lte=entry.date,
                end_date__gte=entry.date,
                status='approved'
            ).exists()
            
            if time_off:
                messages.error(request, f"Сотрудник {employee.full_name} имеет одобренный отгул на эту дату.")
                logger.warning(f"Schedule entry edit failed: employee {employee.id} has approved time off on {entry.date}")
                return redirect('edit_schedule_entry', entry_id=entry_id)
            
            old_employee = entry.employee
            old_equipment = entry.equipment
            old_shift_type = entry.shift_type
            
            entry.employee = employee
            entry.equipment = equipment
            entry.shift_type = shift_type
            entry.save()
            
            logger.info(f"Schedule entry {entry_id} updated: employee {employee.id}, equipment {equipment.id}, shift {shift_type}")
            messages.success(request, "Смена успешно обновлена.")
            return redirect('manager_schedule')
            
        except (Employee.DoesNotExist, Equipment.DoesNotExist) as e:
            messages.error(request, "Произошла ошибка при обновлении смены.")
            logger.error(f"Schedule entry edit failed with error: {str(e)}")
            return redirect('edit_schedule_entry', entry_id=entry_id)
    
    employee_primary_equipment = {}
    for employee in employees:
        primary_skills = EmployeeEquipmentSkill.objects.filter(
            employee=employee,
            skill_level='primary'
        )
        employee_primary_equipment[employee.id] = [skill.equipment_id for skill in primary_skills]
    
    context = {
        'entry': entry,
        'employees': employees,
        'equipment_list': equipment_list,
        'employee_primary_equipment': employee_primary_equipment
    }
    
    return render(request, 'schedule/edit_schedule_entry.html', context)

@login_required
@manager_required
@require_POST
def delete_schedule_entry(request, entry_id):
    logger.info(f"Schedule entry deletion requested by {request.user.email} for entry {entry_id}")
    
    try:
        schedule_entry = get_object_or_404(Schedule, id=entry_id)
        employee_id = schedule_entry.employee.id
        equipment_id = schedule_entry.equipment.id
        date = schedule_entry.date
        shift_type = schedule_entry.shift_type
        
        schedule_entry.delete()
        
        logger.info(f"Schedule entry {entry_id} deleted: employee {employee_id}, equipment {equipment_id}, date {date}, shift {shift_type}")
        messages.success(request, "Смена успешно удалена.")
    except Exception as e:
        logger.error(f"Schedule entry deletion failed with error: {str(e)}")
        messages.error(request, "Произошла ошибка при удалении смены.")
    
    return redirect('manager_schedule')

@login_required
@manager_required
def move_schedule_entry(request, entry_id):
    logger.info(f"Schedule entry move requested by {request.user.email} for entry {entry_id}")
    
    if request.method == 'POST':
        try:
            entry = get_object_or_404(Schedule, id=entry_id)
            new_date_str = request.POST.get('new_date')
            
            if not new_date_str:
                messages.error(request, "Пожалуйста, выберите новую дату.")
                return redirect('manager_schedule')
            
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            
            if Schedule.objects.filter(employee=entry.employee, date=new_date).exists():
                messages.error(request, f"Сотрудник {entry.employee.full_name} уже имеет смену на выбранную дату.")
                return redirect('manager_schedule')
            
            if TimeOffRequest.objects.filter(
                employee=entry.employee,
                start_date__lte=new_date,
                end_date__gte=new_date,
                status='approved'
            ).exists():
                messages.error(request, f"Сотрудник {entry.employee.full_name} имеет одобренный отгул на выбранную дату.")
                return redirect('manager_schedule')
            
            old_date = entry.date
            entry.date = new_date
            entry.save()
            
            logger.info(f"Schedule entry {entry_id} moved from {old_date} to {new_date}")
            messages.success(request, f"Смена успешно перенесена с {old_date.strftime('%d.%m.%Y')} на {new_date.strftime('%d.%m.%Y')}.")
        except Exception as e:
            logger.error(f"Schedule entry move failed with error: {str(e)}")
            messages.error(request, f"Ошибка при переносе смены: {str(e)}")
    
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
    try:
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if User.objects.filter(email=username).exists():
            messages.error(request, f"Пользователь с email {username} уже существует.")
            return redirect('employees')
        
        user = User.objects.create_user(email=username, password=password)
        
        full_name = request.POST.get('full_name')
        role = request.POST.get('role')
        
        employee = Employee.objects.create(
            user=user,
            full_name=full_name,
            email=user.email,
            phone=request.POST.get('phone'),
            rate=request.POST.get('rate'),
            role=role,
            shift_availability=request.POST.get('shift_availability', 'all_shifts')
        )
        
        last_work_day = request.POST.get('last_work_day_prev_month')
        if last_work_day:
            employee.last_work_day_prev_month = datetime.strptime(last_work_day, '%Y-%m-%d').date()
            employee.save()
        
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
    employee = get_object_or_404(Employee, id=employee_id)
    
    try:
        employee.full_name = request.POST.get('full_name')
        employee.phone = request.POST.get('phone')
        employee.rate = request.POST.get('rate')
        employee.role = request.POST.get('role')
        employee.shift_availability = request.POST.get('shift_availability', 'all_shifts')
        
        last_work_day = request.POST.get('last_work_day_prev_month')
        if last_work_day:
            employee.last_work_day_prev_month = datetime.strptime(last_work_day, '%Y-%m-%d').date()
        else:
            employee.last_work_day_prev_month = None
        
        employee.save()
        
        EmployeeEquipmentSkill.objects.filter(employee=employee).delete()
        
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
    employee = get_object_or_404(Employee, id=employee_id)
    
    try:
        if employee.user:
            employee.user.delete()
        
        employee.delete()
        
        messages.success(request, "Сотрудник успешно удален.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при удалении сотрудника: {str(e)}")
    
    return redirect('employees')

@login_required
@manager_required
def equipment(request):
    equipment_list = Equipment.objects.all().order_by('name')
    
    context = {
        'equipment_list': equipment_list
    }
    
    return render(request, 'equipment/equipment_list.html', context)

@login_required
@manager_required
@require_POST
def create_equipment(request):
    try:
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
    equipment = get_object_or_404(Equipment, id=equipment_id)
    try:
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
    equipment = get_object_or_404(Equipment, id=equipment_id)
    try:
        equipment.delete()
        messages.success(request, "Оборудование успешно удалено.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при удалении оборудования: {str(e)}")
    return redirect('equipment')

@login_required
@manager_required
def employee_work_hours(request):
    current_date = datetime.now().date()
    month = request.GET.get('month', current_date.month)
    year = request.GET.get('year', current_date.year)
    try:
        month = int(month)
        year = int(year)
    except ValueError:
        month = current_date.month
        year = current_date.year

    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    working_days = get_working_days_in_month(year, month)
    employees = Employee.objects.all()
    employee_hours = []

    for employee in employees:
        if not EmployeeEquipmentSkill.objects.filter(employee=employee).exists():
            continue
            
        schedules = Schedule.objects.filter(
            employee=employee,
            date__gte=first_day,
            date__lte=last_day
        )
        total_hours = 0
        for schedule in schedules:
            if schedule.shift_type == 'morning':
                total_hours += 6
            elif schedule.shift_type == 'evening':
                total_hours += 6
            elif schedule.shift_type == 'night':
                total_hours += 12

        required_hours = working_days * 6
        if float(employee.rate) == 1.5:
            required_hours = round(required_hours * 1.5)

        employee_hours.append({
            'employee': employee,
            'total_hours': total_hours,
            'required_hours': required_hours,
            'difference': total_hours - required_hours
        })

    employee_hours.sort(key=lambda x: x['employee'].full_name)

    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    context = {
        'employee_hours': employee_hours,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'working_days': working_days,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year
    }
    return render(request, 'employees/employee_work_hours.html', context)