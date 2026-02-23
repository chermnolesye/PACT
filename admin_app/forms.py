from django import forms
from core_app.models import User, Group

class StudentRegistrationForm(forms.ModelForm):
    login = forms.CharField(max_length=100, required=True, label='Логин')
    lastname = forms.CharField(max_length=100, required=True, label='Фамилия')
    firstname = forms.CharField(max_length=100, required=True, label='Имя')
    middlename = forms.CharField(max_length=100, required=False, label='Отчество')
    birthdate = forms.DateField(
        required=False,
        label='Дата рождения',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    gender = forms.ChoiceField(
        choices=[(True, 'Мужской'), (False, 'Женский')],
        required=False,
        label='Пол'
    )
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=True, label='Группа')

    class Meta:
        model = User
        fields = ['login', 'lastname', 'firstname', 'middlename', 'birthdate', 'gender']


class TeacherRegistrationForm(forms.ModelForm):
    login = forms.CharField(max_length=100, required=True, label='Логин')
    lastname = forms.CharField(max_length=100, required=True, label='Фамилия')
    firstname = forms.CharField(max_length=100, required=True, label='Имя')
    middlename = forms.CharField(max_length=100, required=False, label='Отчество')
    birthdate = forms.DateField(
        required=False,
        label='Дата рождения',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    gender = forms.ChoiceField(
        choices=[(True, 'Мужской'), (False, 'Женский')],
        required=False,
        label='Пол'
    )

    class Meta:
        model = User
        fields = ['login', 'lastname', 'firstname', 'middlename', 'birthdate', 'gender']