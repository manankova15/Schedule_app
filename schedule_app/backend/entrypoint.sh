#!/bin/bash

echo "Waiting for PostgreSQL..."
while ! nc -z -v -w30 $POSTGRES_HOST $POSTGRES_PORT; do
  echo "Waiting for PostgreSQL to start..."
  sleep 2
done
echo "PostgreSQL started"

mkdir -p staticfiles
mkdir -p media
mkdir -p static
mkdir -p templates

echo "Initializing database with required tables..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f /app/init_db.sql

echo "Applying database migrations..."
python manage.py migrate --fake-initial

echo "Creating superuser..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
exec gunicorn hospital.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --reload