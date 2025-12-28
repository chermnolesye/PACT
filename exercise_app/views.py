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
from django_filters.views import FilterView
from .filters import ExerciseFilter, ReviewTextFilter, GradingTextFilter
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
    ExerciseTextTask,
    AcademicYear,
    Group,
    TextType
)
from .forms import (
    AddExerciseForm,
    AddExerciseTextForm,
    EditExerciseForm,
    EditTextForm,
    AddErrorAnnotationForm,
    ExerciseTextTaskForm,
    Group,
    AddMarkForm,
    TeacherCommentForm
)

'''
    ОБЩИЙ БЕК
'''

def get_teacher_fio(request):
    return request.session.get("teacher_fio", "")

def load_exercise_data(request):
    exercise_id = request.GET.get('exerciseId')
    if exercise_id:
        exercise_to_edit = get_object_or_404(Exercise, idexercise=exercise_id)
        data = {
            'id': exercise_to_edit.idexercise,
            'creationdate': exercise_to_edit.creationdate,
            'deadline': exercise_to_edit.deadline
        }
        return JsonResponse(data)    
    return JsonResponse({})

@user_passes_test(has_teacher_rights, login_url='/auth/login/')
def teacher_exercises(request):
    exercise_filter = ExerciseFilter(request.GET, queryset=Exercise.objects.all())
    # exercises_queryset = exercise_filter.qs
    exercises_queryset = exercise_filter.qs.order_by(
        '-completiondate', # последние завершенные первыми
        '-exercisemark', # сначала без оценки
        '-exercisestatus',  # сдано -> не сдано
        'creationdate',  # сначала созданные раньше
        '-deadline',      # ближайшие дедлайны первыми
    )
    exercises_list = []
    for exercise in exercises_queryset:
        in_time = False
        if exercise.exercisestatus and exercise.completiondate:
            in_time = exercise.completiondate <= exercise.deadline
        else:
            in_time = datetime.date.today() <= exercise.deadline
        
        exercises_dict = {
            'exercise_data': exercise,
            'in_time': in_time
        }
        exercises_list.append(exercises_dict)
    edit_form = EditExerciseForm(initial={
         'creationdate': datetime.date.today(),
         'deadline': datetime.date.today(),
    })
    context = {
        'exercises' : exercises_list,
        'filter': exercise_filter,
        'edit_form': edit_form
        }
    if request.method == "POST":
        if 'edit_text' in request.POST:
            edit_form = EditExerciseForm(request.POST)
            if edit_form.is_valid():
                exercise_to_edit = get_object_or_404(Exercise, idexercise=edit_form.cleaned_data['exercise_id'])
                exercise_to_edit.creationdate = edit_form.cleaned_data['creationdate']
                exercise_to_edit.deadline = edit_form.cleaned_data['deadline']
                exercise_to_edit.save()
                return redirect('teacher_exercises')
            else:
                edit_form = EditExerciseForm(request.POST)       
    return render(request, 'teacher_exercises.html', context)

@require_POST
@csrf_exempt
def delete_exercise_ajax(request, exercise_id):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        exercise = get_object_or_404(Exercise, idexercise=exercise_id)
        exercise.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@user_passes_test(has_teacher_rights, login_url='/auth/login/')    
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
                            idexercisetext=form.cleaned_data['review_exercisetext_obj'],
                            idexercisetexttask=form.cleaned_data['review_task_obj']
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

    review_texts = ExerciseText.objects.all()
    grading_texts = Text.objects.all().order_by('idtext')[:10]
    context = {
        "form": form,
        "review_texts": review_texts,
        "grading_texts": grading_texts,
        "academic_years": AcademicYear.objects.all(),  # Для фильтра "Учебный год"
        "text_types": TextType.objects.all(),
    }
    return render(request, "add_exercise.html", context)

def get_grading_texts(request):
    try:
        queryset = Text.objects.filter(textgrade__isnull=False)
        exclude_student_id = request.GET.get('exclude_student')
        if exclude_student_id:
            try:
                # ВОЗМОЖНО, на курсы ниже тоже нужно исключать тексты
                queryset = queryset.exclude(idstudent_id=int(exclude_student_id))
            except (ValueError, TypeError):
                pass
        filtered_texts = GradingTextFilter(request.GET, queryset=queryset)
        texts = filtered_texts.qs.order_by('-createdate')
        texts_data = [
            {
                'id': text.idtext,
                'header': text.header,
                'student': text.idstudent.get_full_name(),
                'group': str(text.idstudent.idgroup),
                'academic_year': str(text.idstudent.idgroup.idayear),
                'text_type': str(text.idtexttype) if text.idtexttype else '',
                'created_date': text.createdate.strftime('%d.%m.%Y') if text.createdate else '',
                'grade': text.get_textgrade_display(),
            }
            for text in texts
        ]
        return JsonResponse(texts_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def get_review_texts(request):
    try:
        texts = ExerciseText.objects.all().order_by('-loaddate')
        
        texts_data = [
            {
                'id': text.idexercisetext,
                'name': text.exercisetextname,
                'author': text.author,
                'load_date': text.loaddate.strftime('%d.%m.%Y'),
            }
            for text in texts
        ]
        
        return JsonResponse(texts_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def get_text_tasks(request, text_id):
    try:
        tasks = ExerciseTextTask.objects.filter(idexercisetext=text_id)
        print(len(tasks))
        tasks_data = [
            {
                'id': task.idexercisetexttask,
                'title': task.tasktitle,
                'text': task.tasktext
            }
            for task in tasks
        ]
        return JsonResponse(tasks_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

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
@user_passes_test(has_teacher_rights, login_url='/auth/login/')
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
                # return redirect('add_review_text')
                return redirect('review_text', idexercisetext=exercise_text.idexercisetext)
                
            except Exception as e:
                print("Form errors:", {str(e)}) 
    else:
        form = AddExerciseTextForm()
    
    return render(request, 'add_review_text.html', {'form': form})

@user_passes_test(has_teacher_rights, login_url='/auth/login/')
def review_teacher(request, idexercise=1):
    exercise = get_object_or_404(Exercise, idexercise=idexercise)
    exercisereview = get_object_or_404(ExerciseReview, idexercise=idexercise)
    exercisetext = exercisereview.idexercisetext
    text = get_object_or_404(ExerciseText, idexercisetext=exercisetext.idexercisetext)
    # print("айди текста", exercisetext.idexercisetext)

    reviews = ExerciseFragmentReview.objects.filter(
        idexercisereview=exercisereview
    ).order_by('startposition')
    total_reviews = reviews.count()

    processed_text = wrap_fragments_with_spans(text.exercisetext, reviews)

    in_time = False
    if exercise.exercisestatus and exercise.completiondate:
        in_time = exercise.completiondate <= exercise.deadline

    # ФОРМА ДЛЯ ВЫСТАВЛЕНИЯ ОЦЕНКИ
    if request.method == "POST" and "mark-form" in request.POST:
        mark_form = AddMarkForm(request.POST, instance=exercise)
        if mark_form.is_valid():
            mark_form.save()
            return redirect(request.path + f"?idexercise={exercise.idexercise}")
    else:
        mark_form = AddMarkForm(instance=exercise)

    fragment_forms = {}
    for review in reviews:
        fragment_forms[review.idexercisetextreview] = TeacherCommentForm(
            instance=review,
            prefix=f'comment_{review.idexercisetextreview}'
        )
    
    context = {
        'exercise': exercise,
        'exercisereview': exercisereview,
        'text_metadata': text,
        'text': processed_text,
        'reviews': reviews,
        'total_reviews': total_reviews,
        'in_time': in_time,
        'mark_form': mark_form,
        'teacher_comment_form': TeacherCommentForm(),  # Пустая форма для AJAX
        'fragment_forms': fragment_forms,
        'fragments_json': json.dumps([  # Добавляем JSON с данными фрагментов
            {
                'id': r.idexercisetextreview,
                'review': r.review,
                'teachercomment': r.teachercomment or '',
                'has_comment': bool(r.teachercomment)
            }
            for r in reviews
        ])
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
            f'data-teacher-comment="{fragment.teachercomment or ""}">'
        )
        print(f"offset before: {offset}")
        result = result[:start] + span_tag + result[start:end] + '</span>' + result[end:]
        offset += len(span_tag) + len('</span>')
        # offset += end
        print(f"offset after: {offset}, len span = {len(span_tag)}")
    return result

def update_teacher_comment(request, fragment_id):
    if request.method == 'POST':
        fragment = get_object_or_404(ExerciseFragmentReview, pk=fragment_id)
        # Проверяем AJAX запрос
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = TeacherCommentForm(request.POST, instance=fragment)
            if form.is_valid():
                form.save()
                return JsonResponse({
                    'success': True,
                    'comment': fragment.teachercomment or '',
                    'has_comment': bool(fragment.teachercomment),
                    'message': 'Комментарий сохранен'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
        else:
            form = TeacherCommentForm(request.POST, instance=fragment)
            if form.is_valid():
                form.save()
                return redirect(request.META.get('HTTP_REFERER', '/'))
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def delete_teacher_comment(request, fragment_id):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        fragment = get_object_or_404(ExerciseFragmentReview, pk=fragment_id)
        fragment.teachercomment = ''
        fragment.save()
        return JsonResponse({
            'success': True,
            'message': 'Комментарий удален',
            'has_comment': False
        })
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@user_passes_test(has_teacher_rights, login_url='/auth/login/')
def review_text_list(request):
    reviewtext_filter = ReviewTextFilter(request.GET, queryset=ExerciseText.objects.all())
    texts = reviewtext_filter.qs.order_by('-loaddate')
    # texts = ExerciseText.objects.all()
    context = {'texts' : texts, 'filter': reviewtext_filter}
    return render(request, 'review_text_list.html', context)

@user_passes_test(has_teacher_rights, login_url='/auth/login/')
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
@user_passes_test(has_teacher_rights, login_url='/auth/login/')
def grade_text(request, idexercise=2):
    exercise = get_object_or_404(Exercise, idexercise=idexercise)
    
    in_time = False
    if exercise.exercisestatus and exercise.completiondate:
        in_time = exercise.completiondate <= exercise.deadline

    exercise_grading = get_object_or_404(ExerciseGrading, idexercise=idexercise)
    
    text_id = exercise_grading.idtext
    if text_id:
        text = get_object_or_404(Text, idtext=text_id.idtext)
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
            
            exercise_error_tokens = token.exerciseerrortoken_set.select_related(
                "idexerciseerror__iderrortag", "idexerciseerror__iderrorlevel", "idexerciseerror__idreason", "idexerciseerror"
            ).filter(idexercisegrading_id=idexercise)
            
            exercise_errors_list = []

            for eet in exercise_error_tokens:
                exerror = eet.idexerciseerror
                if exerror and exerror.iderrortag:
                    exercise_errors_list.append({
                        "error_tag_id": exerror.iderrortag,
                        "error_id": exerror.idexerciseerror,
                        "error_tag": exerror.iderrortag.tagtext,
                        "error_tag_russian": exerror.iderrortag.tagtextrussian,
                        "error_tag_abbrev": exerror.iderrortag.tagtextabbrev,
                        "error_color": exerror.iderrortag.tagcolor,
                        "error_level": exerror.iderrorlevel.errorlevelname if error.iderrorlevel else "Не указано",
                        "error_correct": exerror.correct or "Не указано",
                        "error_comment": exerror.comment or "Не указано",
                        "error_reason": exerror.idreason.reasonname if exerror.idreason else "Не указано",
                        "idtagparent": exerror.iderrortag.idtagparent,
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
                "exercise_errors": exercise_errors_list,
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

    # ФОРМА ДЛЯ ВЫСТАВЛЕНИЯ ОЦЕНКИ
    if request.method == "POST" and "mark-form" in request.POST:
         mark_form = AddMarkForm(request.POST, instance=exercise)
         if mark_form.is_valid():
             mark_form.save()
             return redirect(request.path + f"?idexercise={exercise.idexercise}")
    else:
         mark_form = AddMarkForm(instance=exercise)

    student = text.idstudent
    user = student.iduser
    group = student.idgroup
    text_type = text.idtexttype

    context = {
        "mark_form": mark_form,
        "text": text,
        "annotation_form": annotation_form,
        "sentence_data": sentence_data,
        "exercise": exercise,
        "exercise_grading":exercise_grading,
        "in_time":in_time,
        "selected_markup": selected_markup,
        "poscheckflag": text.poscheckflag,
        "errorcheckflag": text.errorcheckflag,
    }
    return render(request, "grade_text.html", context)

def grading_student(request):
    return render(request, "grading_student.html")

