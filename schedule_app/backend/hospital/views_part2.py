from datetime import datetime, timedelta, date
import calendar
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum, Count, Case, When, IntegerField
import random

from api.models import (
    Employee, Equipment, Schedule, EmployeeEquipmentSkill, TimeOffRequest
)
from .views import is_manager, manager_required, generate_calendar_days, get_shift_info

User = get_user_model()

def get_working_days_in_month(year, month):
    """Calculate the number of working days in a given month (excluding weekends)"""
    cal = calendar.monthcalendar(year, month)
    working_days = 0
    for week in cal:
        for day in week:
            if day != 0 and calendar.weekday(year, month, day) < 5:
                working_days += 1
    return working_days

def get_available_employees(employees, date, shift_type, equipment):
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
    """Manager schedule view"""
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
    """Schedule generator view"""
    """Schedule generator view using combined Hopcroft-Karp algorithm and rules-based approach for optimal schedule generation"""
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
                    diff_days = (end_date - start_date).days + 1
                    
                    if diff_days > 31:
                        error = "Период не должен превышать 31 день"
                    else:
                        Schedule.objects.filter(date__gte=start_date, date__lte=end_date).delete()
                        
                        employees = Employee.objects.all()
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
                                
                                weight = 1
                                
                                skill = EmployeeEquipmentSkill.objects.filter(
                                    employee=employee,
                                    equipment=equipment
                                ).first()
                                
                                if skill:
                                    if skill.skill_level == 'primary':
                                        weight += 50
                                    else:
                                        weight += 15
                                    
                                    if employee.shift_availability == 'morning_only':
                                        if not is_weekend and shift_type == 'morning':
                                            weight += 100
                                        elif is_weekend or shift_type != 'morning':
                                            weight -= 100
                                    
                                    elif employee.shift_availability == 'all_shifts':
                                        if is_weekend:
                                            if shift_type == 'morning':
                                                weight += 30
                                            else:
                                                morning_shift = (date, equipment_id, 'morning')
                                                if morning_shift in shift_nodes and (employee.id, morning_shift) in edges:
                                                    weight += 100
                                        else:
                                            if shift_type in ['evening', 'night']:
                                                weight += 30
                                    
                                    time_off = TimeOffRequest.objects.filter(
                                        employee=employee,
                                        start_date__lte=date,
                                        end_date__gte=date,
                                        status='approved'
                                    ).first()
                                    
                                    if time_off:
                                        weight -= 50
                                    else:
                                        pending_time_off = TimeOffRequest.objects.filter(
                                            employee=employee,
                                            start_date__lte=date,
                                            end_date__gte=date
                                        ).first()
                                        
                                        if pending_time_off:
                                            if pending_time_off.priority == 'low':
                                                weight -= 10
                                            elif pending_time_off.priority == 'medium':
                                                weight -= 20
                                            elif pending_time_off.priority == 'high':
                                                weight -= 30
                                    
                                    prev_day_schedule = Schedule.objects.filter(
                                        employee=employee,
                                        date=date - timedelta(days=1)
                                    ).exists()
                                    
                                    if prev_day_schedule:
                                        if employee.shift_availability != 'morning_only':
                                            weight -= 50
                                    
                                    same_day_schedule = Schedule.objects.filter(
                                        employee=employee,
                                        date=date
                                    ).exists()
                                    
                                    if same_day_schedule:
                                        if employee.shift_availability == 'all_shifts' and is_weekend:
                                            weight += 20
                                        else:
                                            weight -= 50
                                    
                                    current_workload = employee_shifts + employee_workload.get(employee.id, 0)
                                    
                                    current_date_month = date.month
                                    current_date_year = date.year
                                    working_days_in_month = get_working_days_in_month(current_date_year, current_date_month)
                                    required_hours = working_days_in_month * 6
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
                                    
                                    shift_hours = 0
                                    if shift_type == 'morning':
                                        shift_hours = 6
                                    elif shift_type == 'evening':
                                        shift_hours = 6
                                    elif shift_type == 'night':
                                        shift_hours = 12
                                    
                                    hours_after_shift = current_hours + shift_hours
                                    
                                    if hours_after_shift > required_hours + 12:
                                        continue
                                    elif hours_after_shift > required_hours:
                                        weight -= (hours_after_shift - required_hours) * 5
                                    elif hours_after_shift < required_hours:
                                        remaining_hours = required_hours - hours_after_shift
                                        weight += min(remaining_hours * 2, 30)
                                    
                                    if shift_type == 'night':
                                        prev_night = Schedule.objects.filter(
                                            employee=employee,
                                            shift_type='night',
                                            date__lt=date
                                        ).order_by('-date').first()
                                        if prev_night:
                                            days_since_last_night = (date - prev_night.date).days
                                            if days_since_last_night < 2:
                                                continue
                                            elif days_since_last_night == 2:
                                                weight -= 100

                                    if shift_type == 'night' and employee.shift_availability == 'all_shifts':
                                        n_nights_past = Schedule.objects.filter(
                                            employee=employee,
                                            shift_type='night',
                                            date__month=current_date_month,
                                            date__year=current_date_year,
                                        ).count()
                                        n_nights_future = 0
                                        for edge, w in edges.items():
                                            eid, snode = edge
                                            if (eid == employee.id and snode[2] == 'night' and
                                                snode[0].month == current_date_month and
                                                snode[0].year == current_date_year):
                                                n_nights_future += 1
                                        total_nights = n_nights_past + n_nights_future
                                        avg_nights = (
                                            len([s for s in shift_nodes if s[2] == 'night' and
                                                 s[0].month == current_date_month and
                                                 s[0].year == current_date_year]) /
                                            (len([e for e in employees if e.shift_availability == 'all_shifts']) or 1)
                                        )
                                        if total_nights > avg_nights + 1:
                                            continue
                                        elif total_nights > avg_nights:
                                            weight -= 80

                                    if shift_type == 'night' and employee.shift_availability == 'all_shifts':
                                        n_nights_for_employee = Schedule.objects.filter(
                                            employee=employee,
                                            shift_type='night',
                                            date__month=current_date_month,
                                            date__year=current_date_year,
                                        ).count()
                                        avg_nights = (
                                            len([s for s in shift_nodes if s[2] == 'night' and
                                                 s[0].month == current_date_month and
                                                 s[0].year == current_date_year]) /
                                            (len([e for e in employees if e.shift_availability == 'all_shifts']) or 1)
                                        )
                                        max_nights = int(avg_nights + 1)
                                        if n_nights_for_employee >= max_nights:
                                            continue
                                    
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
                        
                        matching = final_matching
                        
                        for (employee_id, shift_node) in matching:
                            date, equipment_id, shift_type = shift_node
                            Schedule.objects.create(
                                employee=Employee.objects.get(id=employee_id),
                                equipment=Equipment.objects.get(id=equipment_id),
                                date=date,
                                shift_type=shift_type
                            )
                        
                        success = True
                        messages.success(request, "Расписание успешно сгенерировано с использованием алгоритма Хопкрофта-Карпа!")
                        return redirect('manager_schedule')
            except ValueError:
                error = "Неверный формат даты"
            except Exception as e:
                error = f"Произошла ошибка при генерации расписания: {str(e)}"
    
    context = {
        'error': error,
        'success': success,
        'form': {
            'start_date': {'value': request.POST.get('start_date', '')},
            'end_date': {'value': request.POST.get('end_date', '')}
        }
    }
    
    return render(request, 'schedule/schedule_generator.html', context)

def find_maximum_weighted_matching(employee_nodes, shift_nodes, edges):
    """
    Implementation of the Hopcroft-Karp algorithm for maximum weighted bipartite matching.
    Returns a list of (employee_id, shift_node) pairs representing the optimal matching.
    """
    employee_workload = {employee_id: 0 for employee_id in employee_nodes}
    sorted_edges = sorted(edges.items(), key=lambda x: x[1], reverse=True)
    matching = []
    assigned_employees = {}
    assigned_shifts = set()
    
    for (employee_id, shift_node), weight in sorted_edges:
        if shift_node in assigned_shifts:
            continue
            
        date, _, _ = shift_node
        
        has_shift_today = False
        if employee_id in assigned_employees:
            for s_node in assigned_employees[employee_id]:
                if s_node[0] == date:
                    has_shift_today = True
                    break
                
        employee = Employee.objects.get(id=employee_id)
        is_weekend = date.weekday() >= 5
        if has_shift_today and not (employee.shift_availability == 'all_shifts' and is_weekend):
            continue
            
        matching.append((employee_id, shift_node))
        if employee_id not in assigned_employees:
            assigned_employees[employee_id] = []
        assigned_employees[employee_id].append(shift_node)
        assigned_shifts.add(shift_node)
        employee_workload[employee_id] += 1
    
    return matching

def apply_scheduling_rules(initial_matching, employee_nodes, shift_nodes, edges, day_workers, on_call_workers):
    """
    A specialized algorithm to apply scheduling rules to an initial matching:
    1. Day workers work morning shifts on weekdays
    2. On-call workers work evening and night shifts on weekdays
    3. On-call workers work all shifts on weekends (same worker for all shifts on the same day)
    4. Balance workload among employees
    """
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
    
    matching_dict = {}
    for employee_id, shift_node in initial_matching:
        matching_dict[shift_node] = employee_id
    
    employee_workload = {employee_id: 0 for employee_id in employee_nodes}
    for employee_id, _ in initial_matching:
        employee_workload[employee_id] += 1
    
    for date, date_shifts in shifts_by_date.items():
        is_weekend = date.weekday() >= 5
        
        if not is_weekend:
            morning_shifts = [shift for shift in date_shifts if shift[2] == 'morning']
            
            for shift in morning_shifts:
                if shift in matching_dict and matching_dict[shift] in [worker.id for worker in day_workers]:
                    continue
                
                best_day_worker = None
                best_weight = float('-inf')
                
                for worker in day_workers:
                    if (worker.id, shift) in edges:
                        weight = edges[(worker.id, shift)]
                        adjusted_weight = weight - (employee_workload[worker.id] * 5)
                        
                        if adjusted_weight > best_weight:
                            best_weight = adjusted_weight
                            best_day_worker = worker.id
                
                if best_day_worker:
                    if shift in matching_dict:
                        employee_workload[matching_dict[shift]] -= 1
                    
                    matching_dict[shift] = best_day_worker
                    employee_workload[best_day_worker] += 1
    
    for date, date_shifts in shifts_by_date.items():
        is_weekend = date.weekday() >= 5
        
        if not is_weekend:
            evening_night_shifts = [shift for shift in date_shifts if shift[2] in ['evening', 'night']]
            
            for shift in evening_night_shifts:
                if shift in matching_dict and matching_dict[shift] in [worker.id for worker in on_call_workers]:
                    continue
                
                best_on_call_worker = None
                best_weight = float('-inf')
                
                for worker in on_call_workers:
                    if (worker.id, shift) in edges:
                        weight = edges[(worker.id, shift)]
                        adjusted_weight = weight - (employee_workload[worker.id] * 5)
                        
                        if adjusted_weight > best_weight:
                            best_weight = adjusted_weight
                            best_on_call_worker = worker.id
                
                if best_on_call_worker:
                    if shift in matching_dict:
                        employee_workload[matching_dict[shift]] -= 1
                    
                    matching_dict[shift] = best_on_call_worker
                    employee_workload[best_on_call_worker] += 1
    
    for date, equipment_shifts in shifts_by_date_equipment.items():
        is_weekend = date.weekday() >= 5
        
        if is_weekend:
            for equipment_id, shifts in equipment_shifts.items():
                assigned_workers = set()
                for shift in shifts:
                    if shift in matching_dict:
                        worker_id = matching_dict[shift]
                        if worker_id in [w.id for w in on_call_workers]:
                            assigned_workers.add(worker_id)
                
                if len(assigned_workers) == 1 and len(shifts) > 0:
                    continue
                
                best_on_call_worker = None
                best_total_weight = float('-inf')
                
                for worker in on_call_workers:
                    total_weight = 0
                    all_shifts_available = True
                    
                    for shift in shifts:
                        if (worker.id, shift) in edges:
                            total_weight += edges[(worker.id, shift)]
                        else:
                            all_shifts_available = False
                            break
                    
                    if all_shifts_available:
                        adjusted_weight = total_weight - (employee_workload[worker.id] * 5 * len(shifts))
                        
                        if adjusted_weight > best_total_weight:
                            best_total_weight = adjusted_weight
                            best_on_call_worker = worker.id
                
                if best_on_call_worker:
                    for shift in shifts:
                        if shift in matching_dict:
                            employee_workload[matching_dict[shift]] -= 1
                        
                        matching_dict[shift] = best_on_call_worker
                    
                    employee_workload[best_on_call_worker] += len(shifts)
    
    avg_workload = sum(employee_workload.values()) / len(employee_workload) if employee_workload else 0
    overloaded = [e_id for e_id, load in employee_workload.items() if load > avg_workload * 1.5]
    underloaded = [e_id for e_id, load in employee_workload.items() if load < avg_workload * 0.5 and load < 5]
    
    if overloaded and underloaded:
        overloaded_shifts = []
        for shift, employee_id in matching_dict.items():
            if employee_id in overloaded:
                overloaded_shifts.append((shift, employee_id))
        
        overloaded_shifts.sort(key=lambda x: x[0][0], reverse=True)
        
        for shift, current_employee_id in overloaded_shifts:
            if employee_workload[current_employee_id] <= avg_workload:
                continue
                
            date, equipment_id, shift_type = shift
            is_weekend = date.weekday() >= 5
            
            if is_weekend and current_employee_id in [w.id for w in on_call_workers]:
                continue
                
            if shift_type == 'morning' and current_employee_id in [w.id for w in day_workers]:
                continue
            
            best_employee = None
            best_weight = float('-inf')
            
            for employee_id in underloaded:
                if (employee_id, shift) in edges:
                    weight = edges[(employee_id, shift)]
                    
                    conflict = False
                    for other_shift, other_employee in matching_dict.items():
                        if (other_employee == employee_id and other_shift[0] == date):
                            conflict = True
                            break
                    
                    if not conflict and weight > best_weight:
                        best_weight = weight
                        best_employee = employee_id
            
            if best_employee:
                matching_dict[shift] = best_employee
                employee_workload[current_employee_id] -= 1
                employee_workload[best_employee] += 1
                
                if employee_workload[best_employee] >= avg_workload * 0.5:
                    underloaded.remove(best_employee)
    
    final_matching = [(employee_id, shift) for shift, employee_id in matching_dict.items()]
    return final_matching

@login_required
def time_off_requests(request):
    """Time off requests view"""
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
    """Approve time off request"""
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
    """Reject time off request"""
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
        
        if Schedule.objects.filter(employee=employee, date=date).exists():
            messages.error(request, f"Сотрудник {employee.full_name} уже имеет смену на эту дату.")
            return redirect('manager_schedule')
        
        if employee.shift_availability == 'morning_only' and shift_type != 'morning':
            messages.error(request, f"Сотрудник {employee.full_name} может работать только в утреннюю смену.")
            return redirect('manager_schedule')
        
        if employee.shift_availability == 'day_only' and shift_type == 'night':
            messages.error(request, f"Сотрудник {employee.full_name} не может работать в ночную смену.")
            return redirect('manager_schedule')
        
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
    """Update employee"""
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
    """Delete employee"""
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
        equipment.delete()
        messages.success(request, "Оборудование успешно удалено.")
    except Exception as e:
        messages.error(request, f"Произошла ошибка при удалении оборудования: {str(e)}")
    return redirect('equipment')

@login_required
@manager_required
def employee_work_hours(request):
    """View for displaying employee work hours"""
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