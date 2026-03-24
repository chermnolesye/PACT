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
from django.urls import reverse
from django.utils.html import escape
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
    StudentRateGradingTextForm,
    TeacherCommentForm,
    StudentReviewForm
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
    exercise_filter = ExerciseFilter(request.GET, queryset=Exercise.objects.filter(iduserteacher=request.user.iduser).all())
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
        removable = datetime.date.today() < exercise.creationdate

        exercise_name = "nameless"
        exercise_type = exercise.idexercisetype.exerciseabbr
        if exercise_type == 'grading':
            exercise_grading = get_object_or_404(ExerciseGrading, idexercise=exercise.idexercise)
            text_id = exercise_grading.idtext
            text = get_object_or_404(Text, idtext=text_id.idtext)
            exercise_name = text.header[0:20]
        elif exercise_type == 'review':
            exercisereview = get_object_or_404(ExerciseReview, idexercise=exercise.idexercise)
            exercisetext = exercisereview.idexercisetext
            text = get_object_or_404(ExerciseText, idexercisetext=exercisetext.idexercisetext)
            exercise_name = text.exercisetextname[0:10] + " : " + exercisereview.idexercisetexttask.tasktitle[0:7]

        exercises_dict = {
            'exercise_data': exercise,
            'exercise_name': exercise_name,
            'in_time': in_time,
            'removable': removable
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
        student_id = request.GET.get('student_id')
        preselected_student = None

        if student_id:
            preselected_student = get_object_or_404(
                Student.objects.select_related('idgroup', 'idgroup__idayear', 'iduser'),
                idstudent=student_id
            )

        form = AddExerciseForm(preselected_student=preselected_student)

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
        '''exclude_student_id = request.GET.get('exclude_student')
        if exclude_student_id:
            try:
                # ВОЗМОЖНО, на курсы ниже тоже нужно исключать тексты
                queryset = queryset.exclude(idstudent_id=int(exclude_student_id))
            except (ValueError, TypeError):
                pass'''
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
            url = reverse('review_teacher')
            params = f"{exercise.idexercise}/?idexercise={exercise.idexercise}"
            return redirect(url + params)
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
        update_url = reverse('update_teacher_comment', args=[0])
        delete_url = reverse('delete_teacher_comment', args=[0])
        update_student_url = reverse('update_student_review', args=[fragment.idexercisetextreview])
        delete_student_url = reverse('delete_student_review', args=[fragment.idexercisetextreview])
        escaped_comment = escape(fragment.teachercomment or "")
        span_tag = (
            f'<span class="selection" '
            f'data-fragment-id="{fragment.idexercisetextreview}" '
            f'data-review="{fragment.review}" '
            f'data-start="{fragment.startposition}"'
            f'data-end="{fragment.endposition}"'
            f'data-update-student-url="{update_student_url}"'
            f'data-delete-student-url="{delete_student_url}"'
            # f'data-teacher-comment="{fragment.teachercomment or ""}" '
            f'data-teacher-comment="{escaped_comment}" '
            f'data-delete-url="{delete_url}" '
            f'data-update-url="{update_url}">'
        )
        # print(f"offset before: {offset}")
        result = result[:start] + span_tag + result[start:end] + '</span>' + result[end:]
        offset += len(span_tag) + len('</span>')
        # offset += end
        # print(f"offset after: {offset}, len span = {len(span_tag)}")
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

def review_student(request, idexercise=1):
    exercise = get_object_or_404(Exercise, idexercise=idexercise)
    exercisereview = get_object_or_404(ExerciseReview, idexercise=idexercise)
    exercisetext = exercisereview.idexercisetext
    text = get_object_or_404(ExerciseText, idexercisetext=exercisetext.idexercisetext)

    reviews = ExerciseFragmentReview.objects.filter(
        idexercisereview=exercisereview
    ).order_by('startposition')
    total_reviews = reviews.count()

    processed_text = wrap_fragments_with_spans(text.exercisetext, reviews)

    in_time = False
    if exercise.exercisestatus and exercise.completiondate:
        in_time = exercise.completiondate <= exercise.deadline
    from datetime import date
    expired = date.today() > exercise.deadline

    review_form = StudentReviewForm()
    # я хз это надо если проверено уже да?
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
        'original_text_json': json.dumps(text.exercisetext),
        'reviews': reviews,
        'total_reviews': total_reviews,
        'in_time': in_time,
        'expired': expired,
        'review_form': review_form,
        'fragment_forms': fragment_forms,
        'fragments_json': json.dumps([
            {
                'id': r.idexercisetextreview,
                'review': r.review,
                'teachercomment': r.teachercomment or '',
                'has_comment': bool(r.teachercomment)
            }
            for r in reviews
        ])
    }

    # Завершение упражнения
    if request.method == 'POST':
        exercise.exercisestatus = True
        exercise.completiondate = timezone.now().date()
        exercise.save()
        
        return render(request, "review_student.html", context)
    return render(request, "review_student.html", context)



def save_student_review(request, exercise_id):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            try:
                exercise_review = ExerciseReview.objects.get(idexercise_id=exercise_id)
            except ExerciseReview.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'error': f'ExerciseReview с id {exercise_id} не найден'
                })
            review = ExerciseFragmentReview.objects.create(
                idexercisereview=exercise_review,
                review=data['review'],
                startposition=data['startposition'],
                endposition=data['endposition'],
                # selected_text=data['selected_text']
            )
            
            return JsonResponse({
                'success': True,
                'fragment_id': review.idexercisetextreview
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def update_student_review(request, fragment_id):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            
            review = ExerciseFragmentReview.objects.get(pk=fragment_id)
            review.review = data['review']
            review.save()
            
            return JsonResponse({
                'success': True,
                'fragment_id': review.idexercisetextreview
            })
            
        except ExerciseFragmentReview.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Рецензия не найдена'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def delete_student_review(request, fragment_id):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            review = ExerciseFragmentReview.objects.get(pk=fragment_id)
            review.delete()
            
            return JsonResponse({
                'success': True
            })
            
        except ExerciseFragmentReview.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Рецензия не найдена'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
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
    else:
        in_time = datetime.date.today() <= exercise.deadline

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
            ).filter(idexercisegrading_id=exercise_grading.idexercisegrading)
            
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
                        "error_level": exerror.iderrorlevel.errorlevelname if exerror.iderrorlevel else "Не указано",
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
             
             #return redirect(request.path + f"?idexercise={exercise.idexercise}")
             url = reverse('grade_text')
             params = f"{exercise.idexercise}/?idexercise={exercise.idexercise}"
             return redirect(url + params)
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
        "textgrade": exercise_grading.get_textgrade_display() if exercise_grading.textgrade else "Нет данных",
        "completeness": exercise_grading.get_completeness_display() if exercise_grading.completeness else "Нет данных",
        "structure": exercise_grading.get_structure_display() if exercise_grading.structure else "Нет данных",
        "coherence": exercise_grading.get_coherence_display() if exercise_grading.coherence else "Нет данных",
        "in_time":in_time,
        "selected_markup": selected_markup,
        "poscheckflag": text.poscheckflag,
        "errorcheckflag": text.errorcheckflag,
    }
    return render(request, "grade_text.html", context)

# @user_passes_test(has_teacher_rights, login_url='/auth/login/')
def student_grade_text(request, idexercise=2):
    exercise = get_object_or_404(Exercise, idexercise=idexercise)
    
    in_time = False
    if exercise.exercisestatus and exercise.completiondate:
        in_time = exercise.completiondate <= exercise.deadline
    else:
        in_time = datetime.date.today() <= exercise.deadline
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

            exercise_error_tokens = token.exerciseerrortoken_set.select_related(
                "idexerciseerror__iderrortag", "idexerciseerror__iderrorlevel", "idexerciseerror__idreason", "idexerciseerror"
            ).filter(idexercisegrading_id=exercise_grading.idexercisegrading)
            
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
                        "error_level": exerror.iderrorlevel.errorlevelname if exerror.iderrorlevel else "Не указано",
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

        if annotation_form.is_valid():
            try:
                chosen_ids = json.loads(request.POST.get('chosen_ids', '[]'))
                sentences_data = json.loads(request.POST.get('sentences', '[]'))

                print("Chosen IDs:", chosen_ids)
                print("Sentences data:", sentences_data)
                print("Form data:", request.POST)

                with transaction.atomic():
                    new_error = annotation_form.save(commit=False)
                    new_error.correct = annotation_form.cleaned_data.get('correct', '')
                    new_error.changedate = timezone.now()
                    new_error.save()

                    #Если есть новые пустые токены — создаём их
                    for sentence_info in sentences_data:
                        sentence_id = sentence_info['id_sentence']
                        empty_token_positions = sentence_info['empty_token_pos']

                        try:
                            sentence = Sentence.objects.get(idsentence=sentence_id)
                            for position in sorted([int(p) for p in empty_token_positions]):
                                print("Сдвигаем токены начиная с позиции:", position)
                                Token.objects.filter(
                                    idsentence=sentence,
                                    tokenordernumber__gte=position
                                ).update(tokenordernumber=F('tokenordernumber') + 1)
                                # Создаём новый токен
                                new_token = Token.objects.create(
                                    idsentence=sentence,
                                    tokentext='-EMPTY-',  
                                    tokenordernumber=position
                                )
                                print("Создан токен с порядковым номером:", new_token.tokenordernumber)

                                # Добавляем его id в список выделенных 
                                chosen_ids.append(str(new_token.idtoken))
                        except Sentence.DoesNotExist:
                            continue

                    #Привязываем ошибку ко всем выделенным 
                    for token_id in chosen_ids:
                        try:
                            token = Token.objects.get(idtoken=token_id)
                            ExerciseErrorToken.objects.create(idtoken=token, idexerciseerror=new_error,idexercisegrading=exercise_grading)
                        except Token.DoesNotExist:
                            continue
                
                url = reverse('student_grade_text')
                params = f"{exercise.idexercise}/?idexercise={exercise.idexercise}"
                return redirect(url + params)

            except Exception as e:
                print(f"Error saving annotation: {str(e)}")
        else:
            print("Form errors:", annotation_form.errors)
    else:
        annotation_form = AddErrorAnnotationForm()

    if request.method == "POST" and request.POST.get('action') == 'edit':
            print("Мы в функции edit")
            print(request.POST)

            error_id = request.POST.get('error_id')
            if not error_id:
                return JsonResponse({'success': False, 'error': 'Не передан ID аннотации для редактирования'})

            try:
                error = ExerciseError.objects.get(idexerciseerror=error_id)
            except ExerciseError.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Аннотация не найдена'})

            error.iderrortag_id = request.POST.get('id_iderrortag') or error.iderrortag_id
            error.idreason_id= request.POST.get('idreason') or error.idreason_id
            error.iderrorlevel_id = request.POST.get('iderrorlevel') or error.iderrorlevel_id
            error.comment = request.POST.get('comment', '')
            error.correct = request.POST.get('correct', '')
            error.save()

            return JsonResponse({'success': True})
    
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        print("Мы в функции delete")
        error_id = request.POST.get('error_id')
        
        if not error_id:
            return JsonResponse({'success': False, 'error': 'ID ошибки не передан'})

        try:
            error = ExerciseError.objects.get(idexerciseerror=error_id)
        except ExerciseError.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ошибка не найдена'})

        token_ids = list(ExerciseErrorToken.objects.filter(idexerciseerror=error).values_list('idtoken', flat=True))
        tokens_to_check = Token.objects.filter(idtoken__in=token_ids, tokentext='-EMPTY-')

        ExerciseErrorToken.objects.filter(idexerciseerror=error).delete()
        error.delete()

        for token in tokens_to_check:
            if not ExerciseErrorToken.objects.filter(idtoken=token).exists():
                sentence_id = token.idsentence
                order_number = token.tokenordernumber

                token.delete()

                Token.objects.filter(
                    idsentence=sentence_id,
                    tokenordernumber__gt=order_number
                ).update(tokenordernumber=F('tokenordernumber') - 1)

        return JsonResponse({'success': True})
    
    if request.method == 'POST' and request.POST.get('action') == 'submit':
        print("Мы в функции submit")
        exercise.completiondate = timezone.now()
        exercise.exercisestatus = 1
        exercise.save()
        return JsonResponse({'success': True})

    # ФОРМА ДЛЯ ВЫСТАВЛЕНИЯ ОЦЕНКИ
    if request.method == "POST" and "grade-form" in request.POST:
        grade_form = StudentRateGradingTextForm(request.POST, instance=exercise_grading)
        if grade_form.is_valid():
            grade_form.save()
            url = reverse('student_grade_text')
            params = f"{exercise.idexercise}/?idexercise={exercise.idexercise}"
            return redirect(url + params)
    else:
        grade_form = StudentRateGradingTextForm(instance=exercise_grading)

    student = text.idstudent
    user = student.iduser
    group = student.idgroup
    text_type = text.idtexttype
    unmarked_text = (text.text).replace("-EMPTY-","")

    context = {
        "grade_form": grade_form,
        "text": text,
        "annotation_form": annotation_form,
        "sentence_data": sentence_data,
        "exercise": exercise,
        "exercise_grading":exercise_grading,
        "textgrade": exercise_grading.get_textgrade_display() if exercise_grading.textgrade else "Нет данных",
        "completeness": exercise_grading.get_completeness_display() if exercise_grading.completeness else "Нет данных",
        "structure": exercise_grading.get_structure_display() if exercise_grading.structure else "Нет данных",
        "coherence": exercise_grading.get_coherence_display() if exercise_grading.coherence else "Нет данных",
        "in_time":in_time,
        "selected_markup": selected_markup,
        "poscheckflag": text.poscheckflag,
        "errorcheckflag": text.errorcheckflag,
        "unmarked_text": unmarked_text,
    }
    return render(request, "student_grade_text.html", context)

# Поменять на тест с правами студента
# @user_passes_test(has_teacher_rights, login_url='/auth/login/')
def student_exercises(request):
    student_ids = Student.objects.filter(iduser=request.user).values_list('idstudent', flat=True)
    base_queryset = Exercise.objects.filter(idstudent__in=student_ids)
    
    exercise_filter = ExerciseFilter(request.GET, queryset=base_queryset)

    # exercise_filter = ExerciseFilter(request.GET, queryset=Exercise.objects.filter(idstudent=student_id).all())
    # Тут удаляется поле фио студента, потому что оно не нужно
    if 'student_name' in exercise_filter.filters:
        del exercise_filter.filters['student_name']

    exercises_queryset = exercise_filter.qs.order_by(
        '-deadline',      # ближайшие дедлайны первыми
        '-exercisemark', # сначала без оценки
        'exercisestatus',  # не сдано -> сдано
        'creationdate',  # сначала созданные раньше
    )
    exercises_list = []
    for exercise in exercises_queryset:
        in_time = False
        if exercise.exercisestatus and exercise.completiondate:
            in_time = exercise.completiondate <= exercise.deadline
        else:
            in_time = datetime.date.today() <= exercise.deadline
        exercise_name = "nameless"
        exercise_type = exercise.idexercisetype.exerciseabbr
        if exercise_type == 'grading':
            exercise_grading = get_object_or_404(ExerciseGrading, idexercise=exercise.idexercise)
            text_id = exercise_grading.idtext
            text = get_object_or_404(Text, idtext=text_id.idtext)
            exercise_name = text.header[0:20]
        elif exercise_type == 'review':
            exercisereview = get_object_or_404(ExerciseReview, idexercise=exercise.idexercise)
            exercisetext = exercisereview.idexercisetext
            text = get_object_or_404(ExerciseText, idexercisetext=exercisetext.idexercisetext)
            exercise_name = text.exercisetextname[0:10] + " : " + exercisereview.idexercisetexttask.tasktitle[0:7]

        exercises_dict = {
            'exercise_data': exercise,
            'exercise_name': exercise_name,
            'in_time': in_time
        }
        exercises_list.append(exercises_dict)
    context = {
        'exercises' : exercises_list,
        'filter': exercise_filter,
        }
    return render(request, 'student_exercises.html', context)

def grading_student(request):
    return render(request, "grading_student.html")
