import django_filters
from core_app.models import Exercise, ExerciseType, ExerciseTextType, ExerciseText, Text, TextType, Group, AcademicYear
from django import forms
from django.db.models import Q

class ExerciseFilter(django_filters.FilterSet):
    exercisestatus = django_filters.BooleanFilter(
        field_name='exercisestatus',
        label='Статус',
        widget=forms.Select(choices=[('', 'Все'), (True, 'Сдано'), (False, 'Не сдано')])
    )

    exercisemark = django_filters.ChoiceFilter(  # Добавьте это поле!
        choices=Exercise.TASK_RATES,
        label='Оценка',
        empty_label='Все оценки'
    )
    
    student_name = django_filters.CharFilter(
        method='filter_student',
        label='ФИО студента',
        widget=forms.TextInput(attrs={'placeholder': 'Поиск по ФИО'})
    )
    
    idexercisetype = django_filters.ModelChoiceFilter(
        queryset=ExerciseType.objects.all(),
        label='Тип задания',
        empty_label='Все типы'
    )
    
    deadline_after = django_filters.DateFilter(
        field_name='deadline',
        lookup_expr='gte',
        label='Срок сдачи от',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    deadline_before = django_filters.DateFilter(
        field_name='deadline',
        lookup_expr='lte',
        label='Срок сдачи до',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    creationdate_after = django_filters.DateFilter(
        field_name='creationdate',
        lookup_expr='gte',
        label='Дата создания от',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    creationdate_before = django_filters.DateFilter(
        field_name='creationdate',
        lookup_expr='lte',
        label='Дата создания до',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    # Кастомный фильтр для студента
    def filter_student(self, queryset, name, value):
        return queryset.filter(
            Q(idstudent__iduser__firstname__icontains=value) |
            Q(idstudent__iduser__lastname__icontains=value) |
            Q(idstudent__iduser__middlename__icontains=value)
        )
    
    class Meta:
        model = Exercise
        fields = [
            'exercisestatus', 
            'exercisemark', 
            'idexercisetype',
            'student_name',
            'deadline_after',
            'deadline_before',
            'creationdate_after',
            'creationdate_before'
        ]

class ReviewTextFilter(django_filters.FilterSet):
    exercisetextname = django_filters.CharFilter(
        field_name='exercisetextname',
        label='Название',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Поиск по названию'})
    )

    author = django_filters.CharFilter(
        field_name='author',
        label='Автор',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Поиск по автору'})
    )

    idexercisetexttype = django_filters.ModelChoiceFilter(
        field_name='idexercisetexttype',
        queryset=ExerciseTextType.objects.all(),
        label='Тип текстов',
        empty_label='Все типы'
    )

    class Meta:
        model = ExerciseText
        fields = [
            'exercisetextname', 
            'author', 
            'idexercisetexttype'
        ]

class GradingTextFilter(django_filters.FilterSet):
    header = django_filters.CharFilter(
        field_name='header',
        lookup_expr='icontains',
        label='Название текста'
    )
    
    # Фильтр по учебному году через студента -> группа -> учебный год
    academic_year = django_filters.ModelChoiceFilter(
        field_name='idstudent__idgroup__idayear',
        queryset=AcademicYear.objects.all(),
        label='Учебный год'
    )
    
    group = django_filters.ModelChoiceFilter(
        field_name='idstudent__idgroup',
        queryset=Group.objects.all(),
        label='Учебная группа'
    )
    
    text_type = django_filters.ModelChoiceFilter(
        field_name='idtexttype',
        queryset=TextType.objects.all(),
        label='Тип текста'
    )
        
    class Meta:
        model = Text
        fields = ['header', 'academic_year', 'group', 'text_type']
