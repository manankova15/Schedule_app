"""
URL configuration for hospital project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from api.views import (
    EmployeeViewSet, EquipmentViewSet, ScheduleViewSet,
    EmployeeEquipmentSkillViewSet, TimeOffRequestViewSet,
    UserViewSet
)

from hospital import views

# API router
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'equipment', EquipmentViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'skills', EmployeeEquipmentSkillViewSet)
router.register(r'time-off-requests', TimeOffRequestViewSet)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('register-manager/', views.register_manager, name='register_manager'),
    
    # Password reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Main pages
    path('', views.home, name='home'),
    path('my-schedule/', views.my_schedule, name='my_schedule'),
    path('manager-schedule/', views.manager_schedule, name='manager_schedule'),
    
    # Schedule management
    path('schedule-generator/', views.schedule_generator, name='schedule_generator'),
    path('schedule/create/', views.create_schedule_entry, name='create_schedule_entry'),
    path('schedule/delete/<int:entry_id>/', views.delete_schedule_entry, name='delete_schedule_entry'),
    
    # Time off requests
    path('time-off-requests/', views.time_off_requests, name='time_off_requests'),
    path('time-off-requests/new/', views.time_off_request_new, name='time_off_request_new'),
    path('time-off-requests/delete/<int:request_id>/', views.delete_time_off_request, name='delete_time_off_request'),
    path('time-off-requests/approve/<int:request_id>/', views.approve_time_off_request, name='approve_time_off_request'),
    path('time-off-requests/reject/<int:request_id>/', views.reject_time_off_request, name='reject_time_off_request'),
    path('time-off-requests/update-priority/<int:request_id>/', views.update_time_off_request_priority, name='update_time_off_request_priority'),
    
    # Employee management
    path('employees/', views.employees, name='employees'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('employees/update/<int:employee_id>/', views.update_employee, name='update_employee'),
    path('employees/delete/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    
    # Equipment management
    path('equipment/', views.equipment, name='equipment'),
    path('equipment/create/', views.create_equipment, name='create_equipment'),
    path('equipment/update/<int:equipment_id>/', views.update_equipment, name='update_equipment'),
    path('equipment/delete/<int:equipment_id>/', views.delete_equipment, name='delete_equipment'),
]

# Add static and media URLs in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
