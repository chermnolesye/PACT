from django import forms
from core_app.models import (AcademicYear, Error, ErrorTag, ErrorLevel, Reason, 
                             Student, User, Group, Exercise, ExerciseGrading, ExerciseReview, 
                             Text, ExerciseText, ExerciseType, ExerciseTextType, ExerciseTextTask,
                             ExerciseFragmentReview
                            )
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

# class AddExerciseForm(forms.Form):
#     idexercisetype = forms.ModelChoiceField(
#         queryset=ExerciseType.objects.filter(
#             exerciseabbr__in=['grading', 'review']
#         ),
#         label='Тип упражнения',
#         widget=forms.RadioSelect
#     )
#     year = forms.ModelChoiceField(
#         queryset=AcademicYear.objects.all(),
#         label='Учебный год',
#         required=True
#     ) 

#     group = forms.ModelChoiceField(
#         queryset=Group.objects.none(),
#         label='Группа',
#         required=True
#     )   

#     idstudent = forms.ModelChoiceField(
#         queryset=Student.objects.none(),
#         label='Студент, выполняющий упражнение',
#         required=True
#     )
    
#     # creationdate = forms.DateField(
#     #     initial=datetime.date.today,
#     #     label='Дата создания',
#     #     # widget=forms.DateInput(attrs={'type': 'date', 'readonly': 'readonly'})
#     #     widget=forms.DateInput(attrs={
#     #         'type': 'text',  # Меняем на text вместо date
#     #         'readonly': 'readonly',
#     #         'class': 'readonly-date',
#     #         'value': datetime.date.today().strftime('%d.%m.%Y')  # Явно устанавливаем значение
#     #     })
#     # )

#     # я поланаю нужно использовать это:
#     # но надо в шаблоне добавить это поле чтоб ошибок не было

#     creationdate = forms.DateField(
#         initial=datetime.date.today,
#          label='Дата создания',
#          widget=forms.DateInput(attrs={'type': 'date'})
#     )
    
#     deadline = forms.DateField(
#         label='Срок сдачи',
#         widget=forms.DateInput(attrs={'type': 'date'})
#     )

#     # Поле для типа Grading
#     grading_text = forms.ModelChoiceField(
#         queryset=Text.objects.all().order_by('idtext')[:10],
#         label='Текст для поиска ошибок',
#         required=False,
#         # widget=forms.HiddenInput()
#     )
    
#     # Поле для типа Review
#     review_exercisetext = forms.ModelChoiceField(
#         queryset=ExerciseText.objects.all()[:10],
#         label='Текст для рецензирования',
#         required=False,
#         # widget=forms.HiddenInput()
#     )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if self.data:
#                 # Для студентов
#                 if 'year' in self.data:
#                     try:
#                         year_id = int(self.data.get('year'))
#                         self.fields['group'].queryset = Group.objects.filter(idayear=year_id)
#                     except (ValueError, TypeError):
#                         self.fields['group'].queryset = Group.objects.all()
                
#                 if 'group' in self.data:
#                     try:
#                         group_id = int(self.data.get('group'))
#                         self.fields['idstudent'].queryset = Student.objects.filter(idgroup_id=group_id)
#                     except (ValueError, TypeError):
#                         self.fields['idstudent'].queryset = Student.objects.none()
#                 # вероятно то что ниже уже не нужно и надо поменять поля для текстов на инпут для айди
#                 # Для текстов оценивания
#                 if 'grading_text' in self.data:
#                     try:
#                         grading_text_id = int(self.data.get('grading_text'))
#                         self.fields['grading_text'].queryset = Text.objects.filter(idtext=grading_text_id)
#                     except (ValueError, TypeError):
#                         self.fields['grading_text'].queryset = Text.objects.none()
                
#                 # Для текстов рецензирования
#                 if 'review_exercisetext' in self.data:
#                     try:
#                         review_text_id = int(self.data.get('review_exercisetext'))
#                         self.fields['review_exercisetext'].queryset = ExerciseText.objects.filter(idexercisetext=review_text_id)
#                     except (ValueError, TypeError):
#                         self.fields['review_exercisetext'].queryset = ExerciseText.objects.none()
        
#     def clean(self):
#         cleaned_data = super().clean()
#         exercise_type = cleaned_data.get('idexercisetype')
        
#         if exercise_type:
#             exercise_abbr = exercise_type.exerciseabbr
#             if exercise_abbr == 'grading' and not cleaned_data.get('grading_text'):
#                 self.add_error('grading_text', 'Для типа "Оценивание" необходимо выбрать текст')
#             elif exercise_abbr == 'review' and not cleaned_data.get('review_exercisetext'):
#                 self.add_error('review_exercisetext', 'Для типа "Рецензирование" необходимо выбрать текст')
        
#         return cleaned_data

class AddExerciseForm(forms.Form):
    idexercisetype = forms.ModelChoiceField(
        queryset=ExerciseType.objects.filter(
            exerciseabbr__in=['grading', 'review']
        ),
        label='Тип упражнения',
        widget=forms.RadioSelect
    )
    
    year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        label='Учебный год',
        required=True
    ) 
    group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        label='Группа',
        required=True
    )   
    idstudent = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        label='Студент, выполняющий упражнение',
        required=True
    )
    
    creationdate = forms.DateField(
        initial=datetime.date.today,
        label='Дата создания',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    deadline = forms.DateField(
        label='Срок сдачи',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    # Поле для типа Grading
    grading_text = forms.ModelChoiceField(
        # queryset=Text.objects.all().order_by('idtext')[:10],
        queryset=Text.objects.none(),
        label='Текст для поиска ошибок',
        required=False,
        widget=forms.HiddenInput()
    )
    
    # Поля для типа Review
    review_text_id = forms.IntegerField(
        widget=forms.HiddenInput(), 
        required=False,
        label='Текст для рецензирования'
    )
    
    review_task_id = forms.IntegerField(
        widget=forms.HiddenInput(), 
        required=False,
        label='Задание для рецензирования'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data:
            # Для студентов
            if 'year' in self.data:
                try:
                    year_id = int(self.data.get('year'))
                    self.fields['group'].queryset = Group.objects.filter(idayear=year_id)
                except (ValueError, TypeError):
                    self.fields['group'].queryset = Group.objects.all()
            
            if 'group' in self.data:
                try:
                    group_id = int(self.data.get('group'))
                    self.fields['idstudent'].queryset = Student.objects.filter(idgroup_id=group_id)
                except (ValueError, TypeError):
                    self.fields['idstudent'].queryset = Student.objects.none()
            
            # Для текстов оценивания
            if 'grading_text' in self.data:
                # try:
                #     grading_text_id = int(self.data.get('grading_text'))
                #     self.fields['grading_text'].queryset = Text.objects.filter(idtext=grading_text_id)
                # except (ValueError, TypeError):
                #     self.fields['grading_text'].queryset = Text.objects.none()
                try:
                    text_id = int(self.data.get('grading_text'))
                    text = Text.objects.filter(
                        idtext=text_id,
                        textgrade__isnull=False  # Только тексты с оценкой
                    ).first()
                    if text:
                        self.fields['grading_text'].queryset = Text.objects.filter(idtext=text_id)
                except (ValueError, TypeError):
                    self.fields['grading_text'].queryset = Text.objects.none()
                
        
    def clean(self):
        cleaned_data = super().clean()
        exercise_type = cleaned_data.get('idexercisetype')
        
        if exercise_type:
            exercise_abbr = exercise_type.exerciseabbr
            
            if exercise_abbr == 'grading':
                # if not cleaned_data.get('grading_text'):
                #     self.add_error('grading_text', 'Необходимо выбрать текст')
                grading_text = cleaned_data.get('grading_text')
                selected_student = cleaned_data.get('idstudent')
                
                if not grading_text:
                    self.add_error('grading_text', 'Необходимо выбрать текст')
                else:
                    if not grading_text.textgrade:
                        self.add_error('grading_text', 'Выбранный текст не имеет оценки')
                    if selected_student and grading_text.idstudent == selected_student:
                        self.add_error('grading_text', 'Нельзя выбрать текст того же студента, для которого создается упражнение')
            
            elif exercise_abbr == 'review':
                review_text_id = cleaned_data.get('review_text_id')
                review_task_id = cleaned_data.get('review_task_id')
                
                if not review_text_id:
                    self.add_error(None, 'Для типа "Рецензирование" необходимо выбрать текст')
                
                if not review_task_id:
                    self.add_error(None, 'Для типа "Рецензирование" необходимо выбрать задание')
                else:
                    # Получаем объекты для сохранения в cleaned_data
                    try:
                        text_obj = ExerciseText.objects.get(idexercisetext=review_text_id)
                        cleaned_data['review_exercisetext_obj'] = text_obj  # Сохраняем объект
                    except ExerciseText.DoesNotExist:
                        self.add_error('review_text_id', 'Выбранный текст не существует')
                    
                    # Дополнительная проверка, что задание принадлежит тексту
                    try:
                        task_obj = ExerciseTextTask.objects.get(
                            idexercisetexttask=review_task_id,
                            idexercisetext=review_text_id
                        )
                        cleaned_data['review_task_obj'] = task_obj  # Сохраняем объект
                    except ExerciseTextTask.DoesNotExist:
                        self.add_error('review_task_id', 'Выбранное задание не принадлежит тексту')
        
        return cleaned_data

 
class EditExerciseForm(forms.Form):
    exercise_id = forms.IntegerField(widget=forms.HiddenInput())
    creationdate = forms.DateField(
         label='Дата создания',
         widget=forms.DateInput(attrs={'type': 'date'},format='%Y-%m-%d')
    )
    
    deadline = forms.DateField(
        label='Срок сдачи',
        widget=forms.DateInput(attrs={'type': 'date'},format='%Y-%m-%d')
    )

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

class ExerciseTextTaskForm(forms.ModelForm):
    tasktitle = forms.CharField(
        label='Заголовок задания',
        max_length=300,
        required=True
    )
    tasktext = forms.CharField(
        label='Описание задания',
        required=True,
        widget=forms.Textarea()
    )

    class Meta:
        model = ExerciseTextTask
        fields = ['tasktitle', 'tasktext']

class AddMarkForm(forms.ModelForm):
    exercisemark = forms.ChoiceField(
        choices=Exercise.TASK_RATES,
        label="Оценка",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    exercisemarkcomment = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea()
    )

    class Meta:
        model = Exercise
        fields = [
            'exercisemark',
            'exercisemarkcomment'
        ]

class TeacherCommentForm(forms.ModelForm):
    class Meta:
        model = ExerciseFragmentReview
        fields = ['teachercomment']
        widgets = {
            'teachercomment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Введите комментарий'
            })
        }
        labels = {
            'teachercomment': 'Комментарий'
        }