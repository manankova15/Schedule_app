from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="Email")
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Employee(models.Model):
    ROLE_CHOICES = [
        ('staff', 'Сотрудник'),
        ('manager', 'Старшая')
    ]
    
    RATE_CHOICES = [
        (1, '1 ставка'),
        (1.5, '1.5 ставки')
    ]
    
    SHIFT_AVAILABILITY_CHOICES = [
        ('morning_only', 'Только утренняя смена (8:00-14:00)'),
        ('day_only', 'Только дневные смены (8:00-20:00)'),
        ('all_shifts', 'Любые смены')
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Телефон")
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Должность")
    rate = models.FloatField(choices=RATE_CHOICES, default=1, verbose_name="Ставка")
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='staff', verbose_name="Роль")
    shift_availability = models.CharField(
        max_length=50, 
        choices=SHIFT_AVAILABILITY_CHOICES, 
        default='all_shifts',
        verbose_name="Доступность по сменам"
    )
    last_work_day_prev_month = models.DateField(null=True, blank=True, verbose_name="Последний рабочий день в предыдущем месяце")

    def __str__(self):
        return self.full_name

class Equipment(models.Model):
    EQUIPMENT_TYPES = [
        ('mrt', 'МРТ'),
        ('rkt_ge', 'РКТ GE (128 срезовый)'),
        ('rkt_toshiba', 'Тошиба (РКТ 64 срезовый)')
    ]
    
    name = models.CharField(max_length=255, verbose_name="Название")
    equipment_type = models.CharField(max_length=50, choices=EQUIPMENT_TYPES, verbose_name="Тип оборудования")
    shift_morning = models.BooleanField(default=True, verbose_name="Утренняя смена (8:00-14:00)")
    shift_evening = models.BooleanField(default=True, verbose_name="Вечерняя смена (14:00-20:00)")
    shift_night = models.BooleanField(default=False, verbose_name="Ночная смена (20:00-8:00)")

    def __str__(self):
        return self.name

class EmployeeEquipmentSkill(models.Model):
    SKILL_LEVEL = [
        ('primary', 'Основной навык'),
        ('secondary', 'Дополнительный навык')
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='equipment_skills')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVEL, default='primary')
    
    class Meta:
        unique_together = ('employee', 'equipment')
        verbose_name = "Навык работы с оборудованием"
        verbose_name_plural = "Навыки работы с оборудованием"

    def __str__(self):
        return f"{self.employee.full_name} - {self.equipment.name} ({self.get_skill_level_display()})"

class Schedule(models.Model):
    SHIFT_TYPES = [
        ('morning', 'Утро (8:00-14:00)'),
        ('evening', 'Вечер (14:00-20:00)'),
        ('night', 'Ночь (20:00-8:00)')
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='schedules')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    shift_type = models.CharField(max_length=50, choices=SHIFT_TYPES, verbose_name="Тип смены")
    date = models.DateField(verbose_name="Дата")
    
    class Meta:
        unique_together = ('employee', 'date')
        verbose_name = "Расписание"
        verbose_name_plural = "Расписания"

    def __str__(self):
        return f"{self.employee.full_name} - {self.equipment.name} - {self.get_shift_type_display()} - {self.date}"

class TimeOffRequest(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено')
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='time_off_requests')
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    reason = models.TextField(verbose_name="Причина")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='low', verbose_name="Приоритет")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    manager_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий руководителя")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"{self.employee.full_name} - {self.start_date} to {self.end_date} - {self.get_status_display()}"

class ScheduleVersion(models.Model):
    """Model to store versions of schedules for later restoration"""
    name = models.CharField(max_length=255, verbose_name="Название версии")
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='schedule_versions')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    start_date = models.DateField(verbose_name="Дата начала периода")
    end_date = models.DateField(verbose_name="Дата окончания периода")
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    class Meta:
        verbose_name = "Версия расписания"
        verbose_name_plural = "Версии расписания"
        ordering = ['-created_at']

class ScheduleVersionEntry(models.Model):
    """Individual entries for a schedule version"""
    version = models.ForeignKey(ScheduleVersion, on_delete=models.CASCADE, related_name='entries')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    shift_type = models.CharField(max_length=50, choices=Schedule.SHIFT_TYPES, verbose_name="Тип смены")
    date = models.DateField(verbose_name="Дата")
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.equipment.name} - {self.get_shift_type_display()} - {self.date}"
