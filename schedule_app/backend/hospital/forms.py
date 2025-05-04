from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from api.models import Employee

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    
    class Meta:
        model = User
        fields = ('email',)
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class EmployeeRegistrationForm(CustomUserCreationForm):
    full_name = forms.CharField(
        label="ФИО",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    phone = forms.CharField(
        label="Телефон",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    registration_code = forms.CharField(
        label="Код регистрации",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    
    class Meta(CustomUserCreationForm.Meta):
        fields = CustomUserCreationForm.Meta.fields + ('full_name', 'phone', 'registration_code')

# Keep this for backward compatibility but it's no longer used
class ManagerRegistrationForm(CustomUserCreationForm):
    manager_code = forms.CharField(
        label="Код Старшей",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    
    class Meta(CustomUserCreationForm.Meta):
        fields = CustomUserCreationForm.Meta.fields + ('manager_code',)

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'})
    )

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Подтверждение нового пароля",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Текущий пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}),
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Подтверждение нового пароля",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['full_name', 'phone', 'position']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
        }