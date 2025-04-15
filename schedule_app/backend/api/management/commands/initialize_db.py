from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Initialize database with required tables and initial data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database initialization...'))
        
        # Create tables directly if they don't exist
        with connection.cursor() as cursor:
            # Check if auth_user table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'auth_user'
                );
            """)
            auth_user_exists = cursor.fetchone()[0]
            
            if not auth_user_exists:
                self.stdout.write(self.style.WARNING('auth_user table does not exist, creating it...'))
                
                # Create auth_user table
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
                
                # Create auth_group table
                cursor.execute("""
                    CREATE TABLE "auth_group" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "name" varchar(150) NOT NULL UNIQUE
                    );
                """)
                
                # Create auth_permission table
                cursor.execute("""
                    CREATE TABLE "auth_permission" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "name" varchar(255) NOT NULL,
                        "content_type_id" integer NOT NULL,
                        "codename" varchar(100) NOT NULL,
                        UNIQUE ("content_type_id", "codename")
                    );
                """)
                
                # Create auth_group_permissions table
                cursor.execute("""
                    CREATE TABLE "auth_group_permissions" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "group_id" integer NOT NULL,
                        "permission_id" integer NOT NULL,
                        UNIQUE ("group_id", "permission_id")
                    );
                """)
                
                # Create auth_user_groups table
                cursor.execute("""
                    CREATE TABLE "auth_user_groups" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "user_id" integer NOT NULL,
                        "group_id" integer NOT NULL,
                        UNIQUE ("user_id", "group_id")
                    );
                """)
                
                # Create auth_user_user_permissions table
                cursor.execute("""
                    CREATE TABLE "auth_user_user_permissions" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "user_id" integer NOT NULL,
                        "permission_id" integer NOT NULL,
                        UNIQUE ("user_id", "permission_id")
                    );
                """)
                
                # Create django_content_type table
                cursor.execute("""
                    CREATE TABLE "django_content_type" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "app_label" varchar(100) NOT NULL,
                        "model" varchar(100) NOT NULL,
                        UNIQUE ("app_label", "model")
                    );
                """)
                
                # Create django_migrations table
                cursor.execute("""
                    CREATE TABLE "django_migrations" (
                        "id" serial NOT NULL PRIMARY KEY,
                        "app" varchar(255) NOT NULL,
                        "name" varchar(255) NOT NULL,
                        "applied" timestamp with time zone NOT NULL
                    );
                """)
                
                # Create django_session table
                cursor.execute("""
                    CREATE TABLE "django_session" (
                        "session_key" varchar(40) NOT NULL PRIMARY KEY,
                        "session_data" text NOT NULL,
                        "expire_date" timestamp with time zone NOT NULL
                    );
                """)
                
                self.stdout.write(self.style.SUCCESS('Basic auth tables created successfully!'))
        
        # Run migrations to create other tables and update existing ones
        self.stdout.write(self.style.WARNING('Running migrations...'))
        call_command('migrate', '--noinput')
        
        # Create superuser
        self.stdout.write(self.style.WARNING('Creating superuser...'))
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS('Superuser created successfully!'))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser already exists.'))
        
        self.stdout.write(self.style.SUCCESS('Database initialization completed successfully!'))