from django.urls import path
from . import views

urlpatterns = [
    path('teacher_exercises/delete/<int:exercise_id>/', views.delete_exercise_ajax, name='delete_exercise'),
    path('load_students/', views.load_students, name='load_students'),
    path('load_groups/', views.load_groups, name='load_groups'),

    path('add_exercise/', views.add_exercise, name='add_exercise'),
    path('load_exercise_data/', views.load_exercise_data, name='load_exercise_data'),
    path('grading_student/', views.grading_student, name='grading_student'),
    path('texts/', views.get_review_texts, name='get_review_texts'),
    path('reviewtexts/<int:text_id>/tasks/', views.get_text_tasks, name='get_text_tasks'),

    path('add_review_text/', views.add_review_text, name='add_review_text'),
    path('teacher_exercises/', views.teacher_exercises, name='teacher_exercises'),

    path('review_text_list/', views.review_text_list, name='review_text_list'),

    # Тут надо будет одно убрать позже
    path('review_text/', views.review_text, name='review_text'),
    path('review_text/<int:idexercisetext>/', views.review_text, name='review_text'),
    
    path('review_teacher/', views.review_teacher, name='review_teacher'),
    path('review_teacher/<int:idexercise>/', views.review_teacher, name='review_teacher'),
    path('update_comment/<int:fragment_id>/', views.update_teacher_comment, name='update_comment'),

    path('grade_text/', views.grade_text, name='grade_text'),
    path('grade_text/<int:idexercise>/', views.grade_text, name='grade_text'),
   
]