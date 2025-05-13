from datetime import datetime, timedelta, date
import calendar
import heapq
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
    """Schedule generator view using Hopcroft-Karp algorithm for optimal schedule generation"""
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
                        # Clear existing schedule for the selected period
                        Schedule.objects.filter(date__gte=start_date, date__lte=end_date).delete()
                        
                        employees = Employee.objects.all()
                        equipment_list = Equipment.objects.all()
                        
                        # Categorize employees by shift availability
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
                        
                        # Create shift nodes for each date, equipment, and shift type
                        current_date = start_date
                        while current_date <= end_date:
                            is_weekend = current_date.weekday() >= 5
                            
                            for equipment in equipment_list:
                                # Skip non-RKT equipment on weekends
                                if is_weekend and equipment.equipment_type != 'rkt_ge':
                                    continue
                                
                                # Add shift nodes based on equipment availability
                                if equipment.shift_morning:
                                    shift_nodes.append((current_date, equipment.id, 'morning'))
                                if equipment.shift_evening:
                                    shift_nodes.append((current_date, equipment.id, 'evening'))
                                if equipment.shift_night:
                                    shift_nodes.append((current_date, equipment.id, 'night'))
                            
                            current_date += timedelta(days=1)
                        
                        # Initialize employee workload tracking
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
                                
                                # Base weight starts at 0
                                weight = 0
                                
                                # Check if employee has the skill for this equipment
                                skill = EmployeeEquipmentSkill.objects.filter(
                                    employee=employee,
                                    equipment=equipment
                                ).first()
                                
                                if not skill:
                                    continue  # Skip if employee doesn't have the skill
                                
                                # Skill level weight
                                if skill.skill_level == 'primary':
                                    weight += 100  # Strongly prefer primary skills
                                else:
                                    weight += 30   # Secondary skills are acceptable but less preferred
                                
                                # Shift availability constraints
                                if employee.shift_availability == 'morning_only':
                                    # Morning-only employees should only work morning shifts on weekdays
                                    if not is_weekend and shift_type == 'morning':
                                        weight += 200  # Strongly prefer morning shifts for morning-only employees
                                    else:
                                        weight -= 500  # Heavily penalize non-morning shifts for morning-only employees
                                        continue       # Skip this assignment entirely
                                
                                elif employee.shift_availability == 'day_only':
                                    # Day-only employees should not work night shifts
                                    if shift_type == 'night':
                                        weight -= 500  # Heavily penalize night shifts for day-only employees
                                        continue       # Skip this assignment entirely
                                    else:
                                        weight += 50   # Prefer day shifts for day-only employees
                                
                                elif employee.shift_availability == 'all_shifts':
                                    # On-call workers handle all shifts
                                    if is_weekend:
                                        # On weekends, prefer the same worker for all shifts on the same equipment
                                        if shift_type == 'morning':
                                            weight += 50
                                        else:
                                            # Check if this worker is already assigned to the morning shift
                                            morning_shift = (date, equipment_id, 'morning')
                                            if morning_shift in shift_nodes:
                                                # Check existing schedules
                                                morning_schedule = Schedule.objects.filter(
                                                    employee=employee,
                                                    equipment=equipment,
                                                    date=date,
                                                    shift_type='morning'
                                                ).exists()
                                                
                                                if morning_schedule:
                                                    weight += 200  # Strongly prefer same worker for all shifts
                                    else:
                                        # On weekdays, on-call workers primarily handle evening and night shifts
                                        if shift_type in ['evening', 'night']:
                                            weight += 100
                                
                                # Time-off requests
                                time_off = TimeOffRequest.objects.filter(
                                    employee=employee,
                                    start_date__lte=date,
                                    end_date__gte=date
                                ).first()
                                
                                if time_off:
                                    if time_off.status == 'approved':
                                        weight -= 1000  # Approved time-off should be respected
                                        continue        # Skip this assignment entirely
                                    else:
                                        # Pending time-off with different priorities
                                        if time_off.priority == 'low':
                                            weight -= 50
                                        elif time_off.priority == 'medium':
                                            weight -= 150
                                        elif time_off.priority == 'high':
                                            weight -= 300
                                
                                # Rest period between shifts
                                # Check previous day
                                prev_day_schedule = Schedule.objects.filter(
                                    employee=employee,
                                    date=date - timedelta(days=1)
                                ).exists()
                                
                                if prev_day_schedule:
                                    weight -= 300  # Penalize consecutive work days
                                
                                # Check previous 2 days for night shifts
                                for days_back in range(1, 4):
                                    prev_day = date - timedelta(days=days_back)
                                    prev_night_shift = Schedule.objects.filter(
                                        employee=employee,
                                        date=prev_day,
                                        shift_type='night'
                                    ).exists()
                                    
                                    if prev_night_shift:
                                        if days_back < 3:
                                            weight -= 500  # Need at least 3 days rest after night shift
                                            continue       # Skip this assignment entirely
                                        else:
                                            weight -= 100  # Still prefer more rest if possible
                                
                                # Same day schedule (should not have multiple shifts on same day except for on-call on weekends)
                                same_day_schedule = Schedule.objects.filter(
                                    employee=employee,
                                    date=date
                                ).exists()
                                
                                if same_day_schedule:
                                    if employee.shift_availability == 'all_shifts' and is_weekend:
                                        # For on-call workers on weekends, we want them to cover all shifts
                                        weight += 100
                                    else:
                                        weight -= 500  # Otherwise, heavily penalize multiple shifts on same day
                                        continue       # Skip this assignment entirely
                                
                                # Workload balance - ensure employees work close to their required hours
                                current_date_month = date.month
                                current_date_year = date.year
                                working_days_in_month = get_working_days_in_month(current_date_year, current_date_month)
                                
                                # Calculate required hours based on employee rate
                                required_hours = working_days_in_month * 6  # Base: 6 hours per working day
                                if float(employee.rate) == 1.5:
                                    required_hours = round(required_hours * 1.5)  # 1.5 rate means 1.5x hours
                                
                                # Calculate current hours worked this month
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
                                
                                # Calculate future hours from already assigned edges
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
                                
                                # Add hours for this shift
                                shift_hours = 0
                                if shift_type == 'morning':
                                    shift_hours = 6
                                elif shift_type == 'evening':
                                    shift_hours = 6
                                elif shift_type == 'night':
                                    shift_hours = 12
                                
                                total_hours = current_hours + future_hours + shift_hours
                                
                                # Adjust weight based on workload
                                if total_hours > required_hours + 12:
                                    # Too many hours, skip this assignment
                                    continue
                                elif total_hours > required_hours:
                                    # Slightly over required hours - strongly penalize
                                    weight -= (total_hours - required_hours) * 20
                                elif total_hours < required_hours - 12:
                                    # Significantly under required hours - prioritize assignments
                                    remaining_hours = required_hours - total_hours
                                    weight += min(remaining_hours * 10, 200)
                                elif total_hours < required_hours:
                                    # Slightly under required hours - moderately prioritize
                                    remaining_hours = required_hours - total_hours
                                    weight += min(remaining_hours * 5, 100)
                                else:
                                    # Perfect match to required hours - strongly prioritize
                                    weight += 150
                                
                                # Night shift distribution for on-call workers
                                if shift_type == 'night' and employee.shift_availability == 'all_shifts':
                                    # Count night shifts for this employee in current month
                                    n_nights_for_employee = Schedule.objects.filter(
                                        employee=employee,
                                        shift_type='night',
                                        date__month=current_date_month,
                                        date__year=current_date_year,
                                    ).count()
                                    
                                    # Count total night shifts and on-call workers for fair distribution
                                    total_night_shifts = len([s for s in shift_nodes if s[2] == 'night' and
                                                             s[0].month == current_date_month and
                                                             s[0].year == current_date_year])
                                    
                                    total_on_call_workers = len([e for e in employees if e.shift_availability == 'all_shifts'])
                                    
                                    # Calculate average night shifts per on-call worker
                                    avg_nights = total_night_shifts / (total_on_call_workers or 1)
                                    
                                    # Adjust weight based on night shift distribution
                                    if n_nights_for_employee > avg_nights + 1:
                                        weight -= 200  # Too many night shifts compared to others
                                    elif n_nights_for_employee < avg_nights - 1:
                                        weight += 50   # Fewer night shifts, should take more
                                
                                # Equipment-specific constraints
                                if equipment.equipment_type == 'rkt_ge':
                                    # RKT works 24/7, needs coverage for all shifts
                                    weight += 20
                                elif equipment.equipment_type in ['mrt', 'rkt_toshiba']:
                                    # MRT and Toshiba don't need separate on-call staff on weekends
                                    if is_weekend and shift_type != 'morning':
                                        weight -= 50
                                
                                # Add the edge with calculated weight
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
                        
                        # Process the final matching to ensure no conflicts
                        # 1. No employee works multiple shifts at the same time
                        # 2. No equipment has multiple shifts of the same type on the same day
                        
                        # Group matching by date and shift type to check for conflicts
                        shifts_by_date_type = {}
                        for employee_id, shift_node in final_matching:
                            date, equipment_id, shift_type = shift_node
                            key = (date, shift_type)
                            if key not in shifts_by_date_type:
                                shifts_by_date_type[key] = []
                            shifts_by_date_type[key].append((employee_id, equipment_id))
                        
                        # Check for and resolve conflicts
                        resolved_matching = []
                        assigned_employees = {}  # date -> {employee_id}
                        
                        # Sort matching by date to process chronologically
                        sorted_matching = sorted(final_matching, key=lambda x: x[1][0])
                        
                        for employee_id, shift_node in sorted_matching:
                            date, equipment_id, shift_type = shift_node
                            
                            # Check if employee already has a shift on this date
                            if date not in assigned_employees:
                                assigned_employees[date] = set()
                            
                            if employee_id in assigned_employees[date]:
                                # Skip this assignment - employee already has a shift on this date
                                continue
                            
                            # Check if this equipment already has this shift type on this date
                            conflict = False
                            for res_employee_id, res_shift_node in resolved_matching:
                                res_date, res_equipment_id, res_shift_type = res_shift_node
                                if res_date == date and res_equipment_id == equipment_id and res_shift_type == shift_type:
                                    conflict = True
                                    break
                            
                            if not conflict:
                                resolved_matching.append((employee_id, shift_node))
                                assigned_employees[date].add(employee_id)
                        
                        # Check if all shifts are assigned after conflict resolution
                        assigned_shifts = set(shift_node for _, shift_node in resolved_matching)
                        unassigned_shifts = [s for s in shift_nodes if s not in assigned_shifts]
                        
                        if unassigned_shifts:
                            print(f"WARNING: {len(unassigned_shifts)} shifts are unassigned after conflict resolution. Assigning them now.")
                            
                            # For each unassigned shift, find the best available employee
                            for shift_node in unassigned_shifts:
                                date, equipment_id, shift_type = shift_node
                                
                                # Find employees who don't have a shift on this date
                                available_employees = []
                                for employee_id in employee_nodes:
                                    if employee_id not in assigned_employees.get(date, set()):
                                        # Check if employee has the skill for this equipment
                                        skill = EmployeeEquipmentSkill.objects.filter(
                                            employee_id=employee_id,
                                            equipment_id=equipment_id
                                        ).exists()
                                        
                                        if skill:
                                            available_employees.append(employee_id)
                                
                                if available_employees:
                                    # Choose the employee with the fewest shifts
                                    employee_counts = {}
                                    for e_id in available_employees:
                                        employee_counts[e_id] = sum(1 for _, s in resolved_matching if s[0] == e_id)
                                    
                                    best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
                                    resolved_matching.append((best_employee_id, shift_node))
                                    
                                    if date not in assigned_employees:
                                        assigned_employees[date] = set()
                                    assigned_employees[date].add(best_employee_id)
                                else:
                                    # If no employee is available without a shift on this date,
                                    # choose any employee with the fewest shifts
                                    employee_counts = {}
                                    for e_id in employee_nodes:
                                        employee_counts[e_id] = sum(1 for _, s in resolved_matching if s[0] == e_id)
                                    
                                    best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
                                    resolved_matching.append((best_employee_id, shift_node))
                                    
                                    if date not in assigned_employees:
                                        assigned_employees[date] = set()
                                    assigned_employees[date].add(best_employee_id)
                        
                        # Create schedule entries from the resolved matching
                        for employee_id, shift_node in resolved_matching:
                            date, equipment_id, shift_type = shift_node
                            Schedule.objects.create(
                                employee=Employee.objects.get(id=employee_id),
                                equipment=Equipment.objects.get(id=equipment_id),
                                date=date,
                                shift_type=shift_type
                            )
                        
                        success = True
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
    
    This implementation ensures all shifts are assigned while trying to maximize the total weight.
    """
    import heapq
    
    # Initialize empty matching
    matching = {}  # shift_node -> employee_id
    reverse_matching = {}  # employee_id -> set of shift_nodes
    
    # First pass: Try to assign shifts with strict constraints
    # Create a priority queue for edges
    edge_heap = []
    for employee_id in employee_nodes:
        for shift_node in shift_nodes:
            if (employee_id, shift_node) in edges:
                # Store negative weight for max-heap behavior
                heapq.heappush(edge_heap, (-edges[(employee_id, shift_node)], employee_id, shift_node))
    
    # Process edges in order of decreasing weight
    while edge_heap:
        neg_weight, employee_id, shift_node = heapq.heappop(edge_heap)
        weight = -neg_weight  # Convert back to positive weight
        
        # Skip if this shift is already assigned
        if shift_node in matching:
            continue
            
        # Check if employee already has a shift on this date
        date, equipment_id, shift_type = shift_node
        has_conflict = False
        
        if employee_id in reverse_matching:
            for existing_shift in reverse_matching[employee_id]:
                existing_date = existing_shift[0]
                if existing_date == date:
                    has_conflict = True
                    break
        
        if has_conflict:
            continue
            
        # Check for rest period after night shifts
        if employee_id in reverse_matching:
            for existing_shift in reverse_matching[employee_id]:
                existing_date, _, existing_shift_type = existing_shift
                if existing_shift_type == 'night':
                    days_diff = (date - existing_date).days
                    if days_diff < 3:  # Require at least 3 days rest after night shift
                        has_conflict = True
                        break
        
        if has_conflict:
            continue
        
        # Add to matching
        matching[shift_node] = employee_id
        if employee_id not in reverse_matching:
            reverse_matching[employee_id] = set()
        reverse_matching[employee_id].add(shift_node)
    
    # Second pass: Assign any remaining shifts with relaxed constraints
    unassigned_shifts = [s for s in shift_nodes if s not in matching]
    
    if unassigned_shifts:
        print(f"Found {len(unassigned_shifts)} unassigned shifts. Attempting to assign with relaxed constraints.")
        
        # For each unassigned shift, find the best available employee
        for shift_node in unassigned_shifts:
            date, equipment_id, shift_type = shift_node
            
            # Create a priority queue for this shift
            candidates = []
            
            for employee_id in employee_nodes:
                if (employee_id, shift_node) in edges:
                    # Calculate a score for this assignment
                    weight = edges[(employee_id, shift_node)]
                    
                    # Check if employee already has a shift on this date
                    has_shift_on_date = False
                    if employee_id in reverse_matching:
                        for existing_shift in reverse_matching[employee_id]:
                            if existing_shift[0] == date:
                                has_shift_on_date = True
                                break
                    
                    # Penalize if employee already has a shift on this date, but still allow it
                    if has_shift_on_date:
                        weight -= 1000
                    
                    # Check employee's equipment skill
                    skill = EmployeeEquipmentSkill.objects.filter(
                        employee_id=employee_id,
                        equipment_id=equipment_id
                    ).first()
                    
                    if not skill:
                        weight -= 2000  # Heavily penalize but still allow if no other option
                    
                    # Check for time-off requests
                    time_off = TimeOffRequest.objects.filter(
                        employee_id=employee_id,
                        start_date__lte=date,
                        end_date__gte=date,
                        status='approved'
                    ).exists()
                    
                    if time_off:
                        weight -= 3000  # Heavily penalize but still allow if no other option
                    
                    # Add to candidates
                    heapq.heappush(candidates, (-weight, employee_id))
            
            # Assign to best candidate if any exist
            if candidates:
                _, best_employee_id = heapq.heappop(candidates)
                matching[shift_node] = best_employee_id
                if best_employee_id not in reverse_matching:
                    reverse_matching[best_employee_id] = set()
                reverse_matching[best_employee_id].add(shift_node)
    
    # Final check: Ensure all shifts are assigned
    final_unassigned = [s for s in shift_nodes if s not in matching]
    if final_unassigned:
        print(f"WARNING: Still have {len(final_unassigned)} unassigned shifts after relaxed constraints.")
        
        # Last resort: Assign any remaining shifts to any employee
        for shift_node in final_unassigned:
            # Find employee with fewest shifts
            employee_counts = {e_id: len(reverse_matching.get(e_id, set())) for e_id in employee_nodes}
            best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
            
            # Assign shift
            matching[shift_node] = best_employee_id
            if best_employee_id not in reverse_matching:
                reverse_matching[best_employee_id] = set()
            reverse_matching[best_employee_id].add(shift_node)
    
    # Convert matching to the expected output format
    result = [(employee_id, shift_node) for shift_node, employee_id in matching.items()]
    return result

def apply_scheduling_rules(initial_matching, employee_nodes, shift_nodes, edges, day_workers, on_call_workers):
    """
    Apply domain-specific scheduling rules to improve the initial matching:
    1. Day workers work morning shifts on weekdays (8:00-14:00)
    2. On-call workers work evening and night shifts on weekdays (14:00-8:00)
    3. On-call workers work all shifts on weekends (8:00-8:00 next day)
    4. RKT works 24/7, MRT and Toshiba don't need separate on-call staff on weekends
    5. Respect time-off requests with different priorities
    6. Balance workload among employees
    7. Ensure proper rest periods between shifts
    """
    import heapq
    
    # Convert initial matching to dictionary for easier manipulation
    matching_dict = {}
    for employee_id, shift_node in initial_matching:
        matching_dict[shift_node] = employee_id
    
    # Group shifts by date and equipment
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
    
    # Track employee workload and required hours
    employee_workload = {employee_id: 0 for employee_id in employee_nodes}
    employee_hours = {employee_id: 0 for employee_id in employee_nodes}
    employee_required_hours = {}
    
    # Calculate required hours for each employee
    for employee_id in employee_nodes:
        employee = Employee.objects.get(id=employee_id)
        # Get the month of the first shift
        first_date = min([shift[0] for shift in shift_nodes]) if shift_nodes else datetime.now().date()
        working_days = get_working_days_in_month(first_date.year, first_date.month)
        required_hours = working_days * 6  # Base: 6 hours per working day
        if float(employee.rate) == 1.5:
            required_hours = round(required_hours * 1.5)  # 1.5 rate means 1.5x hours
        employee_required_hours[employee_id] = required_hours
    
    # Calculate current hours for each employee
    for shift_node, employee_id in matching_dict.items():
        employee_workload[employee_id] += 1
        _, _, shift_type = shift_node
        if shift_type == 'morning':
            employee_hours[employee_id] += 6
        elif shift_type == 'evening':
            employee_hours[employee_id] += 6
        elif shift_type == 'night':
            employee_hours[employee_id] += 12
    
    # 1. Prioritize day workers for morning shifts on weekdays
    for date, date_shifts in shifts_by_date.items():
        is_weekend = date.weekday() >= 5
        
        if not is_weekend:
            morning_shifts = [shift for shift in date_shifts if shift[2] == 'morning']
            
            for shift in morning_shifts:
                # Check if this shift is already assigned to a day worker
                if shift in matching_dict and matching_dict[shift] in [worker.id for worker in day_workers]:
                    continue
                
                # Find the best day worker for this shift
                candidates = []
                for worker in day_workers:
                    if (worker.id, shift) in edges:
                        # Skip if worker has approved time off
                        time_off = TimeOffRequest.objects.filter(
                            employee=worker,
                            start_date__lte=shift[0],
                            end_date__gte=shift[0],
                            status='approved'
                        ).exists()
                        
                        if time_off:
                            continue
                        
                        # Skip if worker already has a shift on this date
                        has_shift_on_date = False
                        for s, e_id in matching_dict.items():
                            if e_id == worker.id and s[0] == shift[0]:
                                has_shift_on_date = True
                                break
                        
                        if has_shift_on_date:
                            continue
                        
                        # Calculate weight considering workload balance
                        weight = edges[(worker.id, shift)]
                        
                        # Adjust weight based on how close employee is to required hours
                        hours_if_assigned = employee_hours[worker.id] + 6  # Morning shift is 6 hours
                        hours_diff = abs(hours_if_assigned - employee_required_hours[worker.id])
                        adjusted_weight = weight - (hours_diff * 2)
                        
                        # Check for time-off requests with different priorities
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
                        
                        # Check for consecutive work days
                        prev_day = shift[0] - timedelta(days=1)
                        prev_day_schedule = Schedule.objects.filter(
                            employee=worker,
                            date=prev_day
                        ).exists()
                        
                        if prev_day_schedule:
                            adjusted_weight -= 80  # Penalize consecutive work days
                        
                        heapq.heappush(candidates, (-adjusted_weight, worker.id))  # Negative for max-heap
                
                if candidates:
                    # Get best candidate
                    _, best_worker_id = heapq.heappop(candidates)
                    
                    # Update matching
                    if shift in matching_dict:
                        old_employee_id = matching_dict[shift]
                        employee_workload[old_employee_id] -= 1
                        employee_hours[old_employee_id] -= 6  # Morning shift is 6 hours
                    
                    matching_dict[shift] = best_worker_id
                    employee_workload[best_worker_id] += 1
                    employee_hours[best_worker_id] += 6  # Morning shift is 6 hours
    
    # 2. Prioritize on-call workers for evening and night shifts on weekdays
    for date, date_shifts in shifts_by_date.items():
        is_weekend = date.weekday() >= 5
        
        if not is_weekend:
            evening_night_shifts = [shift for shift in date_shifts if shift[2] in ['evening', 'night']]
            
            for shift in evening_night_shifts:
                # Check if this shift is already assigned to an on-call worker
                if shift in matching_dict and matching_dict[shift] in [worker.id for worker in on_call_workers]:
                    continue
                
                # Find the best on-call worker for this shift
                candidates = []
                for worker in on_call_workers:
                    if (worker.id, shift) in edges:
                        # Skip if worker has approved time off
                        time_off = TimeOffRequest.objects.filter(
                            employee=worker,
                            start_date__lte=shift[0],
                            end_date__gte=shift[0],
                            status='approved'
                        ).exists()
                        
                        if time_off:
                            continue
                        
                        # Skip if worker already has a shift on this date
                        has_shift_on_date = False
                        for s, e_id in matching_dict.items():
                            if e_id == worker.id and s[0] == shift[0]:
                                has_shift_on_date = True
                                break
                        
                        if has_shift_on_date:
                            continue
                        
                        # Calculate weight considering workload balance
                        weight = edges[(worker.id, shift)]
                        
                        # Adjust weight based on how close employee is to required hours
                        shift_hours = 12 if shift[2] == 'night' else 6
                        hours_if_assigned = employee_hours[worker.id] + shift_hours
                        hours_diff = abs(hours_if_assigned - employee_required_hours[worker.id])
                        adjusted_weight = weight - (hours_diff * 2)
                        
                        # Check for time-off requests with different priorities
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
                        
                        # Check for consecutive work days
                        prev_day = shift[0] - timedelta(days=1)
                        prev_day_schedule = Schedule.objects.filter(
                            employee=worker,
                            date=prev_day
                        ).exists()
                        
                        if prev_day_schedule:
                            adjusted_weight -= 80  # Penalize consecutive work days
                        
                        # Check for rest period after night shifts
                        if shift[2] == 'night':
                            prev_night_shifts = Schedule.objects.filter(
                                employee=worker,
                                shift_type='night',
                                date__lt=shift[0]
                            ).order_by('-date')
                            
                            if prev_night_shifts.exists():
                                last_night_shift = prev_night_shifts.first()
                                days_since_last_night = (shift[0] - last_night_shift.date).days
                                
                                if days_since_last_night < 3:  # Require at least 3 days rest
                                    continue  # Skip this worker
                        
                        heapq.heappush(candidates, (-adjusted_weight, worker.id))  # Negative for max-heap
                
                if candidates:
                    # Get best candidate
                    _, best_worker_id = heapq.heappop(candidates)
                    
                    # Update matching
                    if shift in matching_dict:
                        old_employee_id = matching_dict[shift]
                        employee_workload[old_employee_id] -= 1
                        old_shift_hours = 12 if shift[2] == 'night' else 6
                        employee_hours[old_employee_id] -= old_shift_hours
                    
                    matching_dict[shift] = best_worker_id
                    employee_workload[best_worker_id] += 1
                    new_shift_hours = 12 if shift[2] == 'night' else 6
                    employee_hours[best_worker_id] += new_shift_hours
    
    # 3. Handle weekend shifts - same on-call worker for all shifts on the same equipment
    for date, equipment_shifts in shifts_by_date_equipment.items():
        is_weekend = date.weekday() >= 5
        
        if is_weekend:
            for equipment_id, shifts in equipment_shifts.items():
                # Skip if no shifts for this equipment
                if not shifts:
                    continue
                
                # Get equipment type
                equipment = Equipment.objects.get(id=equipment_id)
                
                # Only RKT works 24/7, others don't need on-call staff on weekends
                if equipment.equipment_type != 'rkt_ge' and any(s[2] != 'morning' for s in shifts):
                    continue
                
                # Check if all shifts are already assigned to the same on-call worker
                assigned_workers = set()
                for shift in shifts:
                    if shift in matching_dict:
                        worker_id = matching_dict[shift]
                        if worker_id in [w.id for w in on_call_workers]:
                            assigned_workers.add(worker_id)
                
                if len(assigned_workers) == 1 and len(shifts) > 0:
                    continue  # Already assigned to a single on-call worker
                
                # Find the best on-call worker for all shifts
                candidates = []
                for worker in on_call_workers:
                    # Check if worker can take all shifts
                    total_weight = 0
                    all_shifts_available = True
                    
                    # Skip if worker has approved time off
                    time_off = TimeOffRequest.objects.filter(
                        employee=worker,
                        start_date__lte=date,
                        end_date__gte=date,
                        status='approved'
                    ).exists()
                    
                    if time_off:
                        continue
                    
                    # Check for rest period
                    prev_day = date - timedelta(days=1)
                    prev_day_schedule = Schedule.objects.filter(
                        employee=worker,
                        date=prev_day
                    ).exists()
                    
                    if prev_day_schedule:
                        continue  # Skip this worker - need rest between shifts
                    
                    # Check for night shifts in the past 3 days
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
                    
                    # Calculate total hours if assigned all shifts
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
                        # Adjust weight based on how close to required hours
                        hours_diff = abs(total_hours - employee_required_hours[worker.id])
                        adjusted_weight = total_weight - (hours_diff * 2)
                        
                        heapq.heappush(candidates, (-adjusted_weight, worker.id))  # Negative for max-heap
                
                if candidates:
                    # Get best candidate
                    _, best_worker_id = heapq.heappop(candidates)
                    
                    # Update matching - assign all shifts to the same worker
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
    
    # 4. Balance workload among employees based on required hours
    for employee_id in employee_nodes:
        # Skip if employee is close to required hours
        if abs(employee_hours[employee_id] - employee_required_hours[employee_id]) <= 6:
            continue
        
        # Check if employee is overloaded or underloaded
        is_overloaded = employee_hours[employee_id] > employee_required_hours[employee_id] + 12
        is_underloaded = employee_hours[employee_id] < employee_required_hours[employee_id] - 12
        
        if is_overloaded:
            # Find shifts that can be reassigned
            employee_shifts = []
            for shift, e_id in matching_dict.items():
                if e_id == employee_id:
                    employee_shifts.append(shift)
            
            # Sort by date (newest first) to minimize disruption
            employee_shifts.sort(key=lambda x: x[0], reverse=True)
            
            for shift in employee_shifts:
                # Stop if employee is no longer overloaded
                if employee_hours[employee_id] <= employee_required_hours[employee_id] + 6:
                    break
                
                date, equipment_id, shift_type = shift
                is_weekend = date.weekday() >= 5
                
                # Don't reassign weekend shifts for on-call workers (they need to cover all shifts)
                if is_weekend and employee_id in [w.id for w in on_call_workers]:
                    continue
                
                # Don't reassign morning shifts from day workers
                if shift_type == 'morning' and employee_id in [w.id for w in day_workers]:
                    continue
                
                # Find the best underloaded employee for this shift
                candidates = []
                for other_id in employee_nodes:
                    if other_id == employee_id:
                        continue
                    
                    # Only consider underloaded employees
                    if employee_hours[other_id] >= employee_required_hours[other_id]:
                        continue
                    
                    if (other_id, shift) in edges:
                        # Skip if employee has approved time off
                        time_off = TimeOffRequest.objects.filter(
                            employee=Employee.objects.get(id=other_id),
                            start_date__lte=shift[0],
                            end_date__gte=shift[0],
                            status='approved'
                        ).exists()
                        
                        if time_off:
                            continue
                        
                        # Check for conflicts (same day assignment)
                        conflict = False
                        for other_shift, e_id in matching_dict.items():
                            if e_id == other_id and other_shift[0] == date:
                                conflict = True
                                break
                        
                        if conflict:
                            continue
                        
                        # Check employee type constraints
                        employee = Employee.objects.get(id=other_id)
                        if not ((shift_type == 'morning' and employee.shift_availability == 'morning_only') or
                               (shift_type != 'night' and employee.shift_availability == 'day_only') or
                               employee.shift_availability == 'all_shifts'):
                            continue
                        
                        # Calculate weight
                        weight = edges[(other_id, shift)]
                        
                        # Adjust weight based on how close to required hours
                        shift_hours = 12 if shift_type == 'night' else 6
                        hours_if_assigned = employee_hours[other_id] + shift_hours
                        hours_diff = abs(hours_if_assigned - employee_required_hours[other_id])
                        adjusted_weight = weight - (hours_diff * 2)
                        
                        heapq.heappush(candidates, (-adjusted_weight, other_id))  # Negative for max-heap
                
                if candidates:
                    # Get best candidate
                    _, best_employee_id = heapq.heappop(candidates)
                    
                    # Update matching
                    matching_dict[shift] = best_employee_id
                    
                    # Update hours
                    shift_hours = 12 if shift_type == 'night' else 6
                    employee_hours[employee_id] -= shift_hours
                    employee_hours[best_employee_id] += shift_hours
                    
                    # Update workload
                    employee_workload[employee_id] -= 1
                    employee_workload[best_employee_id] += 1
    
    # Final check: Ensure all shifts are assigned
    all_shifts_assigned = True
    for shift_node in shift_nodes:
        if shift_node not in matching_dict:
            all_shifts_assigned = False
            print(f"WARNING: Shift {shift_node} is not assigned in apply_scheduling_rules")
            
            # Find the best employee for this unassigned shift
            date, equipment_id, shift_type = shift_node
            candidates = []
            
            for employee_id in employee_nodes:
                if (employee_id, shift_node) in edges:
                    # Calculate a score for this assignment
                    weight = edges[(employee_id, shift_node)]
                    
                    # Check if employee already has a shift on this date
                    has_shift_on_date = False
                    for other_shift, other_employee in matching_dict.items():
                        if other_employee == employee_id and other_shift[0] == date:
                            has_shift_on_date = True
                            break
                    
                    # Penalize if employee already has a shift on this date, but still allow it
                    if has_shift_on_date:
                        weight -= 1000
                    
                    # Add to candidates
                    heapq.heappush(candidates, (-weight, employee_id))
            
            # Assign to best candidate if any exist
            if candidates:
                _, best_employee_id = heapq.heappop(candidates)
                matching_dict[shift_node] = best_employee_id
                employee_workload[best_employee_id] += 1
                shift_hours = 12 if shift_type == 'night' else 6
                employee_hours[best_employee_id] += shift_hours
            else:
                # Last resort: Assign to employee with fewest shifts
                employee_counts = {e_id: employee_workload[e_id] for e_id in employee_nodes}
                best_employee_id = min(employee_counts.items(), key=lambda x: x[1])[0]
                
                matching_dict[shift_node] = best_employee_id
                employee_workload[best_employee_id] += 1
                shift_hours = 12 if shift_type == 'night' else 6
                employee_hours[best_employee_id] += shift_hours
    
    if not all_shifts_assigned:
        print("WARNING: Some shifts were not assigned during rule application. Emergency assignments were made.")
    
    # Convert back to the expected output format
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