from django import forms
from core_app.models import Error, ErrorTag, ErrorLevel, Reason, Student, User, Group, ExerciseGrading, ExerciseReview, Text, ExerciseText, ExerciseType, ExerciseTextType
import datetime
from django.forms import formset_factory

class AddExerciseTextForm(forms.Form):
    # loaddate = forms.DateField(
    #     initial=datetime.date.today,
    #     label='Дата загрузки',
    #     # widget=forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'})
    #     widget=forms.HiddenInput()
    # )

    author = forms.CharField(
        label='Автор текста',
        max_length=300,
        required=True
    )

    idexercisetexttype = forms.ModelChoiceField(
        queryset=ExerciseTextType.objects.all(),
        label='Тип текста',
        required=True,
    )

    exercisetextname = forms.CharField(
        max_length=255,
        label='Название текста',
        required=True,
    )

    exercisetext = forms.CharField(
        label='Текст для рецензии',
        required=True,
        widget=forms.Textarea()
    )

class AddExerciseForm(forms.Form):
    idexercisetype = forms.ModelChoiceField(
        queryset=ExerciseType.objects.filter(
            exerciseabbr__in=['grading', 'review']
        ),
        label='Тип упражнения',
        widget=forms.RadioSelect
    )

    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label='Группа',
        required=True
    )   

    idstudent = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        label='Студент',
        required=True
    )
    
    # creationdate = forms.DateField(
    #     initial=datetime.date.today,
    #     label='Дата создания',
    #     # widget=forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'})
    #     widget=forms.DateInput(attrs={
    #         'type': 'text',  # Меняем на text вместо date
    #         'readonly': 'readonly',
    #         'class': 'readonly-date',
    #         'value': datetime.date.today().strftime('%d.%m.%Y')  # Явно устанавливаем значение
    #     })
    # )
    
    deadline = forms.DateField(
        label='Срок сдачи',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    # Поле для типа Grading
    grading_text = forms.ModelChoiceField(
        queryset=Text.objects.all().order_by('idtext')[:10],
        label='Текст для поиска ошибок',
        required=False,
        # widget=forms.HiddenInput()
    )
    
    # Поле для типа Review
    review_exercisetext = forms.ModelChoiceField(
        queryset=ExerciseText.objects.all()[:10],
        label='Текст для рецензирования',
        required=False,
        # widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Grading texts count:", self.fields['grading_text'].queryset.count())
        print("Review texts count:", self.fields['review_exercisetext'].queryset.count())

        if self.data:
                # Для студентов
                if 'group' in self.data:
                    try:
                        group_id = int(self.data.get('group'))
                        self.fields['idstudent'].queryset = Student.objects.filter(idgroup_id=group_id)
                    except (ValueError, TypeError):
                        self.fields['idstudent'].queryset = Student.objects.none()
                
                # Для текстов оценивания
                if 'grading_text' in self.data:
                    try:
                        grading_text_id = int(self.data.get('grading_text'))
                        self.fields['grading_text'].queryset = Text.objects.filter(idtext=grading_text_id)
                    except (ValueError, TypeError):
                        self.fields['grading_text'].queryset = Text.objects.none()
                
                # Для текстов рецензирования
                if 'review_exercisetext' in self.data:
                    try:
                        review_text_id = int(self.data.get('review_exercisetext'))
                        self.fields['review_exercisetext'].queryset = ExerciseText.objects.filter(idexercisetext=review_text_id)
                    except (ValueError, TypeError):
                        self.fields['review_exercisetext'].queryset = ExerciseText.objects.none()
        
    def clean(self):
        cleaned_data = super().clean()
        exercise_type = cleaned_data.get('idexercisetype')
        
        if exercise_type:
            exercise_abbr = exercise_type.exerciseabbr
            if exercise_abbr == 'grading' and not cleaned_data.get('grading_text'):
                self.add_error('grading_text', 'Для типа "Оценивание" необходимо выбрать текст')
            elif exercise_abbr == 'review' and not cleaned_data.get('review_exercisetext'):
                self.add_error('review_exercisetext', 'Для типа "Рецензирование" необходимо выбрать текст')
        
        return cleaned_data
    
class EditTextForm(forms.Form):
    author = forms.CharField(
        label='Автор текста',
        max_length=300,
        required=True
    )

    idexercisetexttype = forms.ModelChoiceField(
        queryset=ExerciseTextType.objects.all(),
        label='Тип текста',
        required=True,
    )
    exercisetextname = forms.CharField(
        max_length=255,
        label='Название текста',
        required=True,
    )

class AddErrorAnnotationForm(forms.ModelForm):
    iderrortag = forms.ModelChoiceField(
        queryset=ErrorTag.objects.all(),
        label="Выберите тег",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    idreason = forms.ModelChoiceField(
        queryset=Reason.objects.all(),
        label="Причина ошибки",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    iderrorlevel = forms.ModelChoiceField(
        queryset=ErrorLevel.objects.all(),
        label="Степень грубости",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    correct = forms.CharField(
        label="Исправление",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    comment = forms.CharField(
        label="Комментарий",
        widget=forms.Textarea(attrs={'class': 'form-control', "style": "height:50px; min-height:10px;"}),
        required=False
    )

    class Meta:
        model = Error
        fields = ['iderrortag', 'idreason', 'iderrorlevel', 'comment', 'correct']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def get_display_info(self):
        selected_tag = self.cleaned_data.get('iderrortag')
        creator_name = (
            f"{self.user.firstname} {self.user.lastname}"
            if self.user and hasattr(self.user, 'firstname') and hasattr(self.user, 'lastname')
            else "Неизвестный пользователь"
        )
        return {
            'selected_tag': selected_tag.tagtext if selected_tag else '',
            'creator': creator_name
        }
