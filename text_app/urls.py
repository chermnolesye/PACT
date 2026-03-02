from django.urls import path
from . import views


urlpatterns = [
    # path('show_text_markup/', views.show_text_markup, name='show_text_markup'),
    path('show_text_markup/<int:text_id>/', views.show_text_markup, name='show_text_markup'),
    path('annotate_text/', views.annotate_text, name='annotate_text'),
    path('teacher_load_text/', views.teacher_load_text, name='teacher_load_text'),
    path('get_tags/', views.get_tags, name='get_tags'),
    path('search_texts/', views.search_texts, name='search_texts'),
    path('student_search_texts/', views.student_search_texts, name='student_search_texts'),
    path('student_load_text/', views.student_load_text, name='student_load_text'),

    path('student_search_texts/delete/<int:text_id>/', views.delete_text_ajax, name='delete_text'),
]