from django.urls import path
from . import views

urlpatterns = [
    path('teacher_exercise/', views.teacher_exercise, name='teacher_exercise'),
]