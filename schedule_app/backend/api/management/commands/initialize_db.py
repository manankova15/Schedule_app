from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Initialize database with required tables and initial data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database initialization...'))
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'auth_user'
                );
            """)
            auth_user_exists = cursor.fetchone()[0]
            
            if not auth_user_exists:
                self.stdout.write(self.style.WARNING('auth_user table does not exist, creating it...'))
                
                cursor.execute("""
                    CREATE TABLE "auth_user" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "password" varchar(128) NOT NULL,
                        "last_login" timestamp with time zone NULL,
                        "is_superuser" boolean NOT NULL,
                        "username" varchar(150) NOT NULL UNIQUE,
                        "first_name" varchar(150) NOT NULL,
                        "last_name" varchar(150) NOT NULL,
                        "email" varchar(254) NOT NULL,
                        "is_staff" boolean NOT NULL,
                        "is_active" boolean NOT NULL,
                        "date_joined" timestamp with time zone NOT NULL
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "auth_group" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "name" varchar(150) NOT NULL UNIQUE
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "auth_permission" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "name" varchar(255) NOT NULL,
                        "content_type_id" integer NOT NULL,
                        "codename" varchar(100) NOT NULL,
                        UNIQUE ("content_type_id", "codename")
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "auth_group_permissions" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "group_id" integer NOT NULL,
                        "permission_id" integer NOT NULL,
                        UNIQUE ("group_id", "permission_id")
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "auth_user_groups" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "user_id" integer NOT NULL,
                        "group_id" integer NOT NULL,
                        UNIQUE ("user_id", "group_id")
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "auth_user_user_permissions" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "user_id" integer NOT NULL,
                        "permission_id" integer NOT NULL,
                        UNIQUE ("user_id", "permission_id")
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "django_content_type" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "app_label" varchar(100) NOT NULL,
                        "model" varchar(100) NOT NULL,
                        UNIQUE ("app_label", "model")
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "django_migrations" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "app" varchar(255) NOT NULL,
                        "name" varchar(255) NOT NULL,
                        "applied" timestamp with time zone NOT NULL
                    );
                """)
                
                cursor.execute("""
                    CREATE TABLE "django_session" (
                        "session_key" varchar(40) NOT NULL PRIMARY KEY,
                        "session_data" text NOT NULL,
                        "expire_date" timestamp with time zone NOT NULL
                    );
                """)
                
                self.stdout.write(self.style.SUCCESS('Basic auth tables created successfully!'))
        
        self.stdout.write(self.style.WARNING('Running migrations...'))
        call_command('migrate', '--noinput')
        
        self.stdout.write(self.style.WARNING('Creating superuser...'))
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS('Superuser created successfully!'))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser already exists.'))
        
        self.stdout.write(self.style.WARNING('Creating test employees...'))
        
        from api.models import CustomUser, Employee, Equipment, EmployeeEquipmentSkill
        
        equipment_data = [
            {'name': 'МРТ аппарат 1', 'equipment_type': 'mrt'},
            {'name': 'РКТ GE аппарат', 'equipment_type': 'rkt_ge'},
            {'name': 'Тошиба РКТ аппарат', 'equipment_type': 'rkt_toshiba'}
        ]
        
        equipment_objects = []
        for data in equipment_data:
            equipment, created = Equipment.objects.get_or_create(
                name=data['name'],
                defaults={
                    'equipment_type': data['equipment_type'],
                    'shift_morning': True,
                    'shift_evening': True,
                    'shift_night': data['equipment_type'] == 'mrt'
                }
            )
            equipment_objects.append(equipment)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created equipment: {equipment.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Equipment already exists: {equipment.name}'))
        
        employee_data = [
            {'email': 'ivanov@hospital.ru', 'password': 'employee123', 'full_name': 'Иванов Иван Иванович', 'role': 'staff'},
            {'email': 'petrova@hospital.ru', 'password': 'employee123', 'full_name': 'Петрова Мария Сергеевна', 'role': 'staff'},
            {'email': 'sidorov@hospital.ru', 'password': 'employee123', 'full_name': 'Сидоров Алексей Петрович', 'role': 'staff'},
            {'email': 'kuznetsova@hospital.ru', 'password': 'employee123', 'full_name': 'Кузнецова Елена Александровна', 'role': 'staff'},
            {'email': 'smirnov@hospital.ru', 'password': 'employee123', 'full_name': 'Смирнов Дмитрий Николаевич', 'role': 'staff'},
            {'email': 'popova@hospital.ru', 'password': 'employee123', 'full_name': 'Попова Ольга Владимировна', 'role': 'staff'},
            {'email': 'sokolov@hospital.ru', 'password': 'employee123', 'full_name': 'Соколов Андрей Михайлович', 'role': 'staff'},
            {'email': 'novikova@hospital.ru', 'password': 'employee123', 'full_name': 'Новикова Татьяна Игоревна', 'role': 'staff'},
            {'email': 'volkov@hospital.ru', 'password': 'employee123', 'full_name': 'Волков Сергей Анатольевич', 'role': 'staff'},
            {'email': 'morozova@hospital.ru', 'password': 'employee123', 'full_name': 'Морозова Наталья Викторовна', 'role': 'staff'},
            {'email': 'manager@hospital.ru', 'password': 'manager123', 'full_name': 'Иванова Анна Петровна', 'role': 'manager'}
        ]
        
        created_employees = []
        for data in employee_data:
            if not CustomUser.objects.filter(email=data['email']).exists():
                user = CustomUser.objects.create_user(
                    email=data['email'],
                    password=data['password'],
                    is_staff=data['role'] == 'manager'
                )
                
                employee = Employee.objects.create(
                    user=user,
                    full_name=data['full_name'],
                    email=data['email'],
                    role=data['role'],
                    rate=1.5 if data['email'] in ['ivanov@hospital.ru', 'petrova@hospital.ru', 'manager@hospital.ru'] else 1.0,
                    shift_availability='all_shifts'
                )
                
                created_employees.append(employee)
                self.stdout.write(self.style.SUCCESS(f'Created employee: {employee.full_name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Employee already exists: {data["email"]}'))
        
        for employee in created_employees:
            if employee.role == 'staff':
                EmployeeEquipmentSkill.objects.get_or_create(
                    employee=employee,
                    equipment=equipment_objects[0],
                    defaults={'skill_level': 'primary'}
                )
                
                if employee.email in ['ivanov@hospital.ru', 'petrova@hospital.ru', 'sidorov@hospital.ru', 'kuznetsova@hospital.ru', 'smirnov@hospital.ru']:
                    EmployeeEquipmentSkill.objects.get_or_create(
                        employee=employee,
                        equipment=equipment_objects[1],
                        defaults={'skill_level': 'secondary'}
                    )
                
                if employee.email in ['popova@hospital.ru', 'sokolov@hospital.ru', 'novikova@hospital.ru', 'volkov@hospital.ru', 'morozova@hospital.ru']:
                    EmployeeEquipmentSkill.objects.get_or_create(
                        employee=employee,
                        equipment=equipment_objects[2],
                        defaults={'skill_level': 'secondary'}
                    )
        
        for employee in Employee.objects.filter(role='manager'):
            if employee.full_name == employee.email:
                employee.full_name = "Иванова Анна Петровна"
                employee.save()
                self.stdout.write(self.style.SUCCESS(f'Updated manager full name: {employee.full_name}'))
        
        self.stdout.write(self.style.SUCCESS('Test employees created successfully!'))
        self.stdout.write(self.style.SUCCESS('Database initialization completed successfully!'))
        
        self.stdout.write(self.style.SUCCESS('\nTest login credentials:'))
        self.stdout.write(self.style.SUCCESS('Manager: manager@hospital.ru / manager123'))
        for data in employee_data:
            if data['role'] == 'staff':
                self.stdout.write(self.style.SUCCESS(f'Employee: {data["email"]} / {data["password"]}'))