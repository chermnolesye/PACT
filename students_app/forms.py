from django import forms
from core_app.models import User, Student, Group, Rights
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError

class AddStudentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.exclude(iduser__in=Student.objects.values_list('iduser', flat=True)),
        label="Пользователь"
    )
    
    group = forms.ModelChoiceField(queryset=Group.objects.all().order_by('-idayear', 'groupname'), label="Группа")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.login})"

class EditStudentForm(forms.ModelForm):
    GENDER_CHOICES = (
        (True, 'Мужской'),
        (False, 'Женский'),
    )

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label='Пол'
    )

    class Meta:
        model = User
        fields = ['lastname', 'firstname', 'middlename', 'birthdate', 'gender']
        widgets = {
            'birthdate': forms.DateInput(format='%Y-%m-%d',
                attrs={
                'type': 'date',
                'max': timezone.now().date().isoformat()
                }),                
        }
        labels = {
            'lastname': 'Фамилия',
            'firstname': 'Имя',
            'middlename': 'Отчество',
            'birthdate': 'Дата рождения'
        }
    def clean_birthdate(self):
        birthdate = self.cleaned_data.get('birthdate')
        if birthdate and birthdate > timezone.now().date():
            raise ValidationError("Дата рождения не может быть в будущем.")
        return birthdate