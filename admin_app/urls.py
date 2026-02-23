from django.urls import path
from .views import admin_index, students_list, teachers_list, register_student, register_teacher, reset_user_password

urlpatterns = [
    path('', admin_index, name='admin_index'),

    path('students/', students_list, name='admin_students_list'),
    path('teachers/', teachers_list, name='admin_teachers_list'),

    path('register_student/', register_student, name='register_student'),
    path('register_teacher/', register_teacher, name='register_teacher'),

    path('reset_password/<int:iduser>/', reset_user_password, name='admin_reset_password'),
]