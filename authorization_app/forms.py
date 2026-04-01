from django import forms

# ----------------

class LoginForm(forms.Form):
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
