from django import forms
from core_app.models import User, Student, Group, Rights

class StudentLoginForm(forms.Form):
    login = forms.CharField(max_length=100, required=True, label='Логин')
    password = forms.CharField(widget=forms.PasswordInput, required=True, label='Пароль')

class TeacherLoginForm(forms.Form):
    login = forms.CharField(max_length=100, required=True, label='Логин')
    password = forms.CharField(widget=forms.PasswordInput, required=True, label='Пароль')

# ----------------

class LoginForm(forms.Form):
    # login = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'placeholder': 'Логин'}), label='')
    # password = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'placeholder': 'Пароль'}), label='')
    login = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Логин',
            'class': 'form-control'
        }),
        label=''
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Пароль',
            'class': 'form-control password-input'
        }),
        label=''
    )
