-- Create auth_user table
CREATE TABLE IF NOT EXISTS "auth_user" (
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

-- Create auth_group table
CREATE TABLE IF NOT EXISTS "auth_group" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(150) NOT NULL UNIQUE
);

-- Create django_content_type table
CREATE TABLE IF NOT EXISTS "django_content_type" (
    "id" serial NOT NULL PRIMARY KEY,
    "app_label" varchar(100) NOT NULL,
    "model" varchar(100) NOT NULL,
    UNIQUE ("app_label", "model")
);

-- Create auth_permission table
CREATE TABLE IF NOT EXISTS "auth_permission" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(255) NOT NULL,
    "content_type_id" integer NOT NULL,
    "codename" varchar(100) NOT NULL,
    UNIQUE ("content_type_id", "codename"),
    CONSTRAINT "auth_permission_content_type_id_fkey" FOREIGN KEY ("content_type_id") REFERENCES "django_content_type" ("id") ON DELETE CASCADE
);

-- Create auth_group_permissions table
CREATE TABLE IF NOT EXISTS "auth_group_permissions" (
    "id" serial NOT NULL PRIMARY KEY,
    "group_id" integer NOT NULL,
    "permission_id" integer NOT NULL,
    UNIQUE ("group_id", "permission_id"),
    CONSTRAINT "auth_group_permissions_group_id_fkey" FOREIGN KEY ("group_id") REFERENCES "auth_group" ("id") ON DELETE CASCADE,
    CONSTRAINT "auth_group_permissions_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "auth_permission" ("id") ON DELETE CASCADE
);

-- Create auth_user_groups table
CREATE TABLE IF NOT EXISTS "auth_user_groups" (
    "id" serial NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL,
    "group_id" integer NOT NULL,
    UNIQUE ("user_id", "group_id"),
    CONSTRAINT "auth_user_groups_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") ON DELETE CASCADE,
    CONSTRAINT "auth_user_groups_group_id_fkey" FOREIGN KEY ("group_id") REFERENCES "auth_group" ("id") ON DELETE CASCADE
);

-- Create auth_user_user_permissions table
CREATE TABLE IF NOT EXISTS "auth_user_user_permissions" (
    "id" serial NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL,
    "permission_id" integer NOT NULL,
    UNIQUE ("user_id", "permission_id"),
    CONSTRAINT "auth_user_user_permissions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") ON DELETE CASCADE,
    CONSTRAINT "auth_user_user_permissions_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "auth_permission" ("id") ON DELETE CASCADE
);

-- Create django_admin_log table
CREATE TABLE IF NOT EXISTS "django_admin_log" (
    "id" serial NOT NULL PRIMARY KEY,
    "action_time" timestamp with time zone NOT NULL,
    "object_id" text NULL,
    "object_repr" varchar(200) NOT NULL,
    "action_flag" smallint NOT NULL CHECK ("action_flag" >= 0),
    "change_message" text NOT NULL,
    "content_type_id" integer NULL,
    "user_id" integer NOT NULL,
    CONSTRAINT "django_admin_log_content_type_id_fkey" FOREIGN KEY ("content_type_id") REFERENCES "django_content_type" ("id") ON DELETE SET NULL,
    CONSTRAINT "django_admin_log_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth_user" ("id") ON DELETE CASCADE
);

-- Create django_migrations table
CREATE TABLE IF NOT EXISTS "django_migrations" (
    "id" serial NOT NULL PRIMARY KEY,
    "app" varchar(255) NOT NULL,
    "name" varchar(255) NOT NULL,
    "applied" timestamp with time zone NOT NULL
);

-- Create django_session table
CREATE TABLE IF NOT EXISTS "django_session" (
    "session_key" varchar(40) NOT NULL PRIMARY KEY,
    "session_data" text NOT NULL,
    "expire_date" timestamp with time zone NOT NULL
);

-- Create index on django_session.expire_date
CREATE INDEX IF NOT EXISTS "django_session_expire_date_idx" ON "django_session" ("expire_date");

-- Create index on django_admin_log.content_type_id
CREATE INDEX IF NOT EXISTS "django_admin_log_content_type_id_idx" ON "django_admin_log" ("content_type_id");

-- Create index on django_admin_log.user_id
CREATE INDEX IF NOT EXISTS "django_admin_log_user_id_idx" ON "django_admin_log" ("user_id");

-- Create api_customuser table
CREATE TABLE IF NOT EXISTS "api_customuser" (
    "id" serial NOT NULL PRIMARY KEY,
    "password" varchar(128) NOT NULL,
    "last_login" timestamp with time zone NULL,
    "is_superuser" boolean NOT NULL,
    "email" varchar(254) NOT NULL UNIQUE,
    "is_staff" boolean NOT NULL,
    "is_active" boolean NOT NULL,
    "date_joined" timestamp with time zone NOT NULL
);

-- Create api_customuser_groups table
CREATE TABLE IF NOT EXISTS "api_customuser_groups" (
    "id" serial NOT NULL PRIMARY KEY,
    "customuser_id" integer NOT NULL,
    "group_id" integer NOT NULL,
    UNIQUE ("customuser_id", "group_id"),
    CONSTRAINT "api_customuser_groups_customuser_id_fkey" FOREIGN KEY ("customuser_id") REFERENCES "api_customuser" ("id") ON DELETE CASCADE,
    CONSTRAINT "api_customuser_groups_group_id_fkey" FOREIGN KEY ("group_id") REFERENCES "auth_group" ("id") ON DELETE CASCADE
);

-- Create api_customuser_user_permissions table
CREATE TABLE IF NOT EXISTS "api_customuser_user_permissions" (
    "id" serial NOT NULL PRIMARY KEY,
    "customuser_id" integer NOT NULL,
    "permission_id" integer NOT NULL,
    UNIQUE ("customuser_id", "permission_id"),
    CONSTRAINT "api_customuser_user_permissions_customuser_id_fkey" FOREIGN KEY ("customuser_id") REFERENCES "api_customuser" ("id") ON DELETE CASCADE,
    CONSTRAINT "api_customuser_user_permissions_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "auth_permission" ("id") ON DELETE CASCADE
);

-- Create api_equipment table
CREATE TABLE IF NOT EXISTS "api_equipment" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(100) NOT NULL,
    "equipment_type" varchar(50) NOT NULL,
    "shift_morning" boolean NOT NULL,
    "shift_evening" boolean NOT NULL,
    "shift_night" boolean NOT NULL
);

-- Create api_employee table
CREATE TABLE IF NOT EXISTS "api_employee" (
    "id" serial NOT NULL PRIMARY KEY,
    "full_name" varchar(100) NOT NULL,
    "email" varchar(254) NOT NULL,
    "phone" varchar(20) NULL,
    "position" varchar(50) NULL,
    "rate" varchar(20) NULL,
    "role" varchar(20) NOT NULL,
    "shift_availability" varchar(50) NOT NULL DEFAULT 'all_shifts',
    "last_work_day_prev_month" date NULL,
    "user_id" integer NULL UNIQUE,
    CONSTRAINT "api_employee_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "api_customuser" ("id") ON DELETE CASCADE
);

-- Create api_employeeequipmentskill table
CREATE TABLE IF NOT EXISTS "api_employeeequipmentskill" (
    "id" serial NOT NULL PRIMARY KEY,
    "skill_level" varchar(20) NOT NULL,
    "employee_id" integer NOT NULL,
    "equipment_id" integer NOT NULL,
    CONSTRAINT "api_employeeequipmentskill_employee_id_fkey" FOREIGN KEY ("employee_id") REFERENCES "api_employee" ("id") ON DELETE CASCADE,
    CONSTRAINT "api_employeeequipmentskill_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "api_equipment" ("id") ON DELETE CASCADE,
    CONSTRAINT "api_employeeequipmentskill_employee_id_equipment_id_key" UNIQUE ("employee_id", "equipment_id")
);

-- Create api_schedule table
CREATE TABLE IF NOT EXISTS "api_schedule" (
    "id" serial NOT NULL PRIMARY KEY,
    "date" date NOT NULL,
    "shift_type" varchar(20) NOT NULL,
    "employee_id" integer NOT NULL,
    "equipment_id" integer NOT NULL,
    CONSTRAINT "api_schedule_employee_id_fkey" FOREIGN KEY ("employee_id") REFERENCES "api_employee" ("id") ON DELETE CASCADE,
    CONSTRAINT "api_schedule_equipment_id_fkey" FOREIGN KEY ("equipment_id") REFERENCES "api_equipment" ("id") ON DELETE CASCADE
);

-- Create api_timeoffrequest table
CREATE TABLE IF NOT EXISTS "api_timeoffrequest" (
    "id" serial NOT NULL PRIMARY KEY,
    "start_date" date NOT NULL,
    "end_date" date NOT NULL,
    "reason" text NOT NULL,
    "status" varchar(20) NOT NULL,
    "priority" varchar(20) NOT NULL,
    "manager_comment" text NULL,
    "created_at" timestamp with time zone NOT NULL,
    "employee_id" integer NOT NULL,
    CONSTRAINT "api_timeoffrequest_employee_id_fkey" FOREIGN KEY ("employee_id") REFERENCES "api_employee" ("id") ON DELETE CASCADE
);

-- Create indexes for foreign keys
CREATE INDEX IF NOT EXISTS "api_employeeequipmentskill_employee_id_idx" ON "api_employeeequipmentskill" ("employee_id");
CREATE INDEX IF NOT EXISTS "api_employeeequipmentskill_equipment_id_idx" ON "api_employeeequipmentskill" ("equipment_id");
CREATE INDEX IF NOT EXISTS "api_schedule_employee_id_idx" ON "api_schedule" ("employee_id");
CREATE INDEX IF NOT EXISTS "api_schedule_equipment_id_idx" ON "api_schedule" ("equipment_id");
CREATE INDEX IF NOT EXISTS "api_timeoffrequest_employee_id_idx" ON "api_timeoffrequest" ("employee_id");