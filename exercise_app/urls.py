from django.urls import path
from . import views

urlpatterns = [
    path('teacher_exercises/delete/<int:exercise_id>/', views.delete_exercise_ajax, name='delete_exercise'),

    path('add_exercise/', views.add_exercise, name='add_exercise'),
    path('grading_student/', views.grading_student, name='grading_student'),    
    path('review_student/', views.review_student, name='review_student'),
    path('load_students/', views.load_students, name='load_students'),
    path('add_exercise_text/', views.add_exercise_text, name='add_exercise_text'),
    path('teacher_exercises/', views.teacher_exercises, name='teacher_exercises'),
   
]