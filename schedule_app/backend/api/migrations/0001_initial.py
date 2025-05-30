import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Employee",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("full_name", models.CharField(max_length=255)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("phone", models.CharField(max_length=20, unique=True)),
                ("position", models.CharField(max_length=100)),
                ("shift_quota", models.IntegerField()),
                (
                    "role",
                    models.CharField(
                        choices=[("staff", "Сотрудник"), ("manager", "Менеджер")],
                        max_length=50,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Equipment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("shift_morning", models.BooleanField(default=True)),
                ("shift_evening", models.BooleanField(default=True)),
                ("shift_night", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="Schedule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "shift_type",
                    models.CharField(
                        choices=[
                            ("morning", "Утро"),
                            ("evening", "Вечер"),
                            ("night", "Ночь"),
                        ],
                        max_length=50,
                    ),
                ),
                ("date", models.DateField()),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.employee"
                    ),
                ),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.equipment"
                    ),
                ),
            ],
        ),
    ]
