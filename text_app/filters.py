import django_filters
from django import forms
from core_app.models import Text, TextType, AcademicYear

class StudentTextFilter(django_filters.FilterSet):
    header = django_filters.CharFilter(
        lookup_expr='icontains', 
        label="Название",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск...'})
    )

    idtexttype = django_filters.ModelChoiceFilter(
        queryset=TextType.objects.all(),
        label="Тип текста",
        empty_label="Все типы"
    )
    
    year = django_filters.ModelChoiceFilter(
        field_name='idstudent__idgroup__idayear',
        # queryset=AcademicYear.objects.all(),
        queryset=AcademicYear.objects.none(),
        label="Учебный год",
        empty_label="Все годы",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_graded = django_filters.BooleanFilter(
        field_name='textgrade',
        method='filter_check',
        label="Статус проверки",
        widget=forms.Select(choices=[
            ('', 'Все'),
            (True, 'Проверено'),
            (False, 'Не проверено')
        ])
    )

    def filter_check(self, queryset, name, value):
        if value is True:
            return queryset.filter(textgrade__isnull=False)
        elif value is False:
            return queryset.filter(textgrade__isnull=True)
        return queryset

    class Meta:
        model = Text
        fields = ['idtexttype', 'year', 'header']

    def __init__(self, *args, **kwargs):
        user = kwargs.get('request').user if kwargs.get('request') else None
        super().__init__(*args, **kwargs)
        # В фильтрах отображаются только те учебные года, в которые учился User
        if user and user.is_authenticated:
            qs = AcademicYear.objects.filter(group__student__iduser=user).distinct().order_by('-title')
            self.filters['year'].extra['queryset'] = qs
            self.form.fields['year'].queryset = qs
