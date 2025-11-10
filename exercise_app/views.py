from authorization_app.utils import has_teacher_rights
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render,  redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import datetime
from core_app.models import (
    ExerciseTextType,
    Exercise,
    ExerciseError,
    ExerciseErrorToken,
    ExerciseFragmentReview,
    ExerciseGrading,
    ExerciseReview,
    ExerciseText,
    ExerciseType,
    Text,
    Student,
    User
)

from .forms import (
    AddExerciseForm,
    AddExerciseTextForm
)


def teacher_exercises(request):
    # if request.method == 'POST':
        # if 'delete_exercise' in request.POST:

    exercises = Exercise.objects.all()

    context = {'exercises' : exercises}
    return render(request, 'teacher_exercises.html', context)

@require_POST
@csrf_exempt
def delete_exercise_ajax(request, exercise_id):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        exercise = get_object_or_404(Exercise, idexercise=exercise_id)
        exercise.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})
    

def add_exercise(request):
    if request.method == 'POST':
        form = AddExerciseForm(request.POST)
        print("POST data:", request.POST) 
        if form.is_valid():
            try:
                # transaction - если одна из операций завершится с ошибкой,
                # значит не выполнится ни одна операция.
                with transaction.atomic():
                    print(request.user)
                    exercise = Exercise(
                        idexercisetype=form.cleaned_data['idexercisetype'],
                        idstudent=form.cleaned_data['idstudent'],
                        iduserteacher=request.user,
                        # creationdate=form.cleaned_data['creationdate'],
                        creationdate=datetime.date.today(),
                        deadline=form.cleaned_data['deadline'],
                        exercisestatus=False
                    )
                    exercise.save()
                    
                    # В зависимости от типа exerciseabbr заполняется одна из таблиц
                    exercise_type = exercise.idexercisetype.exerciseabbr
                    
                    if exercise_type == 'grading':
                        ExerciseGrading.objects.create(
                            idexercise=exercise,
                            idtext=form.cleaned_data['grading_text']
                        )
                    
                    elif exercise_type == 'review':
                        ExerciseReview.objects.create(
                            idexercise=exercise,
                            idexercisetext=form.cleaned_data['review_exercisetext']
                        )
                
                return redirect('teacher_exercises')
                
            except Exception as e:
                print(f'Ошибка: {str(e)}')
        else:
            print('Форма не валидна')
            print("=== FORM VALIDATION ERRORS ===")
            for field, errors in form.errors.items():
                print(f"Field '{field}': {errors}")
            print("=== END ERRORS ===")
    else:
        form = AddExerciseForm()

    context = {
        "form": form
    }

    return render(request, "add_exercise.html", context)


def load_students(request):
    group_id = request.GET.get('group_id')
    if group_id:
        students = Student.objects.filter(idgroup_id=group_id).order_by('iduser__lastname')
        students_data = []
        for student in students:
            students_data.append({
                'id': student.idstudent,
                'name': student.get_full_name() or f"Студент {student.idstudent}"
            })
        return JsonResponse({'students': students_data})    
    return JsonResponse({'students': []})


def add_exercise_text(request):
    if request.method == 'POST':
        form = AddExerciseTextForm(request.POST)
        print("POST data:", request.POST) 
        if form.is_valid():
            print("Form is valid") 
            try:
                exercise_text = ExerciseText(
                    loaddate=datetime.date.today(),
                    author=form.cleaned_data['author'],
                    idexercisetexttype=form.cleaned_data['idexercisetexttype'],
                    exercisetextname=form.cleaned_data['exercisetextname'],
                    exercisetext=form.cleaned_data['exercisetext']
                )
                exercise_text.save()
                
                print('Текст добавлен')
                return redirect('add_exercise_text')
                
            except Exception as e:
                print("Form errors:", {str(e)}) 
    else:
        form = AddExerciseTextForm()
    
    return render(request, 'add_exercise_text.html', {'form': form})

def grading_student(request):
    return render(request, "grading_student.html")

def review_student(request):
    return render(request, "review_student.html")