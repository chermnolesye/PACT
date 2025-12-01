from authorization_app.utils import has_teacher_rights
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render,  redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
import json
from django.utils import timezone
from django.db.models import F
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
    User,
    Token,
    Error,
    ErrorToken,
    Sentence,
    ExerciseTextTask
)

from .forms import (
    AddExerciseForm,
    AddExerciseTextForm,
    EditTextForm,
    AddErrorAnnotationForm,
    ExerciseTextTaskForm,
    Group
)

'''
    ОБЩИЙ БЕК
'''

def get_teacher_fio(request):
    return request.session.get("teacher_fio", "")

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
                        creationdate=form.cleaned_data['creationdate'],
                        #creationdate=datetime.date.today(),
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

def load_groups(request):
    year_id = request.GET.get('yearId')
    if year_id:
        groups = Group.objects.filter(idayear=year_id).order_by('groupname')
        groups_data = []
        for group in groups:
            groups_data.append({
                'id': group.idgroup,
                'groupname': group.groupname
            })
        return JsonResponse({'groups': groups_data})    
    return JsonResponse({'groups': []})

'''
    БЕК КАТИ
'''

def add_review_text(request):
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
                    exercisetext=form.cleaned_data['exercisetext'].strip()
                )
                exercise_text.save()
                
                print('Текст добавлен')
                return redirect('add_review_text')
                
            except Exception as e:
                print("Form errors:", {str(e)}) 
    else:
        form = AddExerciseTextForm()
    
    return render(request, 'add_review_text.html', {'form': form})

def review_teacher(request, idexercise=1):
    exercise = get_object_or_404(Exercise, idexercise=idexercise)
    exercisereview = get_object_or_404(ExerciseReview, idexercise=idexercise)
    exercisetext = exercisereview.idexercisetext
    text = get_object_or_404(ExerciseText, idexercisetext=exercisetext.idexercisetext)
    print("айди текста", exercisetext.idexercisetext)

    reviews = ExerciseFragmentReview.objects.filter(
        idexercisereview=exercisereview
    ).order_by('startposition')

    processed_text = wrap_fragments_with_spans(text.exercisetext, reviews)

    in_time = False
    # if exercise.exercisestatus:
    #     in_time = datetime.date(exercise.deadline) < datetime.date(exercise.completiondate)
    if exercise.exercisestatus and exercise.completiondate:
        in_time = exercise.completiondate <= exercise.deadline

    # print("="*50)
    # print(text.exercisetext)
    # print("="*50)
    context = {
        'exercise': exercise,
        'exercisereview': exercisereview,
        'text_metadata': text,
        'text': processed_text,
        'reviews': reviews,
        'in_time': in_time
    }
    return render(request, "review_teacher.html", context)

def wrap_fragments_with_spans(text, reviews):
    if not reviews:
        return text
    
    fragments = sorted(reviews, key=lambda x: x.startposition)
    result = text
    offset = 0
    
    for fragment in fragments:
        start = fragment.startposition + offset
        end = fragment.endposition + offset
        
        span_tag = (
            f'<span class="selection" '
            f'data-fragment-id="{fragment.idexercisetextreview}" '
            f'data-review="{fragment.review}" '
            f'data-teacher-comment="{fragment.teachercomment}">'
        )
        print(f"offset before: {offset}")
        result = result[:start] + span_tag + result[start:end] + '</span>' + result[end:]
        offset += len(span_tag) + len('</span>')
        # offset += end
        print(f"offset after: {offset}, len span = {len(span_tag)}")
    return result

def review_text_list(request):

    texts = ExerciseText.objects.all()

    context = {'texts' : texts}
    return render(request, 'review_text_list.html', context)

def review_text(request, idexercisetext=2):
    text = get_object_or_404(ExerciseText, idexercisetext=idexercisetext)
    tasks = ExerciseTextTask.objects.filter(idexercisetext=idexercisetext)
    # text.exercisetext = text.exercisetext.strip()
    exercises_count = ExerciseReview.objects.filter(idexercisetext=idexercisetext).count()
    edit_form = EditTextForm(initial={
        'author': text.author,
        'idexercisetexttype': text.idexercisetexttype,
        'exercisetextname': text.exercisetextname,
    })
    add_task_form = ExerciseTextTaskForm()

    if request.method == "POST":
        form_type = request.POST.get('form_type')
        
        if form_type == 'create_task':
            create_form = ExerciseTextTaskForm(request.POST)
            if create_form.is_valid():
                task = create_form.save(commit=False)
                task.idexercisetext = text
                task.save()
                return redirect('review_text', idexercisetext=idexercisetext)
                
        elif form_type == 'update_task':
            task_id = request.POST.get('task_id')
            task = get_object_or_404(ExerciseTextTask, pk=task_id)
            form = ExerciseTextTaskForm(request.POST, instance=task)
            if form.is_valid():
                form.save()
                return redirect('review_text', idexercisetext=idexercisetext)
                
        elif form_type == 'delete_task':
                task_id = request.POST.get('task_id')
                task = get_object_or_404(ExerciseTextTask, pk=task_id)
                task.delete()
                return redirect('review_text', idexercisetext=idexercisetext)        

        elif 'delete_text' in request.POST:
            text.delete()
            return redirect('review_text_list')     

        elif 'edit_text' in request.POST:
            edit_form = EditTextForm(request.POST)
            if edit_form.is_valid():
                text.author = edit_form.cleaned_data['author']
                text.idexercisetexttype = edit_form.cleaned_data['idexercisetexttype']
                text.exercisetextname = edit_form.cleaned_data['exercisetextname']
                text.save()
                return redirect('review_text', idexercisetext=idexercisetext)
            else:
                edit_form = EditTextForm(request.POST)
        
    text_using = f"Текст используется в {exercises_count} упражнени" + get_count_end(exercises_count)

    show_del_btn = True if exercises_count == 0 else False

    task_forms = []
    for task in tasks:
        task_forms.append(ExerciseTextTaskForm(instance=task))

    context = {
        'text': text,
        'tasks': tasks,
        'task_forms': task_forms,
        'exercises_count': exercises_count, # По сути уже не надо это передавать но пока пусть будет
        'show_del_btn': show_del_btn,
        'text_using': text_using,
        'edit_form': edit_form,
        'add_task_form': add_task_form
    }

    return render(request, "review_text.html", context)

def get_count_end(count):
    if 11 <= count % 100 <= 14:
        return 'ях'
    
    last_digit = count % 10
    
    if last_digit == 1:
        return 'и'
    else:
        return 'ях'

'''
    БЕК ДАШИ
'''

def grade_text(request, text_id=2379):
    text_id = request.GET.get("text_id")
    if text_id:
        text = get_object_or_404(Text, idtext=text_id)
    else:
        text = Text.objects.first()

    sentences = text.sentence_set.all()
    sentence_data = []
    selected_markup = request.GET.get("markup", "tagtext")

    for sentence in sentences:
        tokens = Token.objects.filter(idsentence=sentence).select_related("idpostag").order_by('tokenordernumber')
        tokens_data = []
        for token in tokens:
            pos_tag = token.idpostag.tagtext if token.idpostag else None
            pos_tag_russian = token.idpostag.tagtextrussian if token.idpostag else None
            pos_tag_abbrev = token.idpostag.tagtextabbrev if token.idpostag else None
            pos_tag_color = token.idpostag.tagcolor if token.idpostag else None

            error_tokens = token.errortoken_set.select_related(
                "iderror__iderrortag", "iderror__iderrorlevel", "iderror__idreason", "iderror"
            ).all()

            errors_list = []
            for et in error_tokens:
                error = et.iderror
                if error and error.iderrortag:
                    errors_list.append({
                        "error_tag_id": error.iderrortag,
                        "error_id": error.iderror,
                        "error_tag": error.iderrortag.tagtext,
                        "error_tag_russian": error.iderrortag.tagtextrussian,
                        "error_tag_abbrev": error.iderrortag.tagtextabbrev,
                        "error_color": error.iderrortag.tagcolor,
                        "error_level": error.iderrorlevel.errorlevelname if error.iderrorlevel else "Не указано",
                        "error_correct": error.correct or "Не указано",
                        "error_comment": error.comment or "Не указано",
                        "error_reason": error.idreason.reasonname if error.idreason else "Не указано",
                        "idtagparent": error.iderrortag.idtagparent,
                    })

            tokens_data.append({
                "token_id": token.idtoken,
                "token": token.tokentext,
                "pos_tag": pos_tag,
                "pos_tag_russian": pos_tag_russian,
                "pos_tag_abbrev": pos_tag_abbrev,
                "pos_tag_color": pos_tag_color,
                "token_order_number": token.tokenordernumber,
                "errors": errors_list,
            })

        sentence_data.append({
            "id_sentence": sentence.idsentence,
            "sentence": sentence,
            "tokens": tokens_data,
        })
    
    if request.method == "POST" and "annotation-form" in request.POST:
        print("Мы в функции добавления")
        annotation_form = AddErrorAnnotationForm(request.POST, user=request.user)
    else:
        annotation_form = AddErrorAnnotationForm()

    student = text.idstudent
    user = student.iduser
    group = student.idgroup
    text_type = text.idtexttype

    context = {
        "text": text,
        "annotation_form": annotation_form,
        "sentence_data": sentence_data,
        "selected_markup": selected_markup,
        "author": f"{user.lastname} {user.firstname}",
        "group": group.groupname,
        "create_date": text.createdate,
        "text_type": text_type.texttypename if text_type else "Не указано",
        "self_rating": text.get_selfrating_display() if text.selfrating else "Нет данных",
        "self_assesment": text.get_selfassesment_display() if text.selfassesment else "Нет данных",
        "fio": get_teacher_fio(request),
        "textgrade": text.get_textgrade_display() if text.textgrade else "Нет данных",
        "completeness": text.get_completeness_display() if text.completeness else "Нет данных",
        "structure": text.get_structure_display() if text.structure else "Нет данных",
        "coherence": text.get_coherence_display() if text.coherence else "Нет данных",
        "poscheckflag": text.poscheckflag,
        "errorcheckflag": text.errorcheckflag,
        "usererrorcheck": text.idusererrorcheck.get_full_name() if text.idusererrorcheck else "Не указано", 
        "userteacher": text.iduserteacher.get_full_name() if text.iduserteacher else "Не указано", 
    }
    return render(request, "grade_text.html", context)

def grading_student(request):
    return render(request, "grading_student.html")

