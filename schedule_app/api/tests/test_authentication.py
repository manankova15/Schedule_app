import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
from rest_framework import status
from api.models import Employee

User = get_user_model()

@pytest.fixture
def create_user():
    user = User.objects.create_user(
        email='testuser@example.com',
        password='testpassword123'
    )
    
    Employee.objects.create(
        user=user,
        full_name='Test User',
        email='testuser@example.com',
        role='staff'
    )
    
    return user

@pytest.mark.django_db
class TestAuthentication:
    def test_login_success(self, client, create_user):
        url = reverse('login')
        response = client.post(url, {
            'username': 'testuser@example.com',
            'password': 'testpassword123'
        })
        
        assert response.status_code == 302
        assert response.url == reverse('home')
    
    def test_login_failure(self, client):
        url = reverse('login')
        response = client.post(url, {
            'username': 'nonexistent@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
    
    def test_logout(self, client, create_user):
        client.login(username='testuser@example.com', password='testpassword123')
        
        url = reverse('logout')
        response = client.get(url)
        
        assert response.status_code == 302
        assert reverse('login') in response.url
    
    def test_register_view(self, client):
        url = reverse('register')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
    
    def test_register_success(self, client):
        url = reverse('register')
        response = client.post(url, {
            'email': 'newuser@example.com',
            'full_name': 'New User',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'registration_code': 'employee123'
        })
        
        assert response.status_code == 302
        
        assert User.objects.filter(email='newuser@example.com').exists()
        assert Employee.objects.filter(email='newuser@example.com').exists()
    
    def test_access_protected_page_unauthenticated(self, client):
        url = reverse('profile')
        response = client.get(url)
        
        assert response.status_code == 302
        assert reverse('login') in response.url
    
    def test_access_protected_page_authenticated(self, client, create_user):
        client.login(username='testuser@example.com', password='testpassword123')
        
        url = reverse('profile')
        response = client.get(url)
        
        assert response.status_code == 200

@pytest.mark.django_db
class TestJWTAuthentication:
    def test_obtain_jwt_token(self, client, create_user):
        url = reverse('token_obtain_pair')
        response = client.post(url, {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }, content_type='application/json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.json()
        assert 'refresh' in response.json()
    
    def test_refresh_jwt_token(self, client, create_user):
        url = reverse('token_obtain_pair')
        response = client.post(url, {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }, content_type='application/json')
        
        refresh_token = response.json()['refresh']
        
        url = reverse('token_refresh')
        response = client.post(url, {
            'refresh': refresh_token
        }, content_type='application/json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.json()
    
    def test_api_access_with_jwt(self, create_user):
        client = APIClient()
        
        url = reverse('token_obtain_pair')
        response = client.post(url, {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }, format='json')
        
        token = response.json()['access']
        
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('employee-list')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_api_access_without_jwt(self):
        client = APIClient()
        url = reverse('employee-list')
        response = client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
