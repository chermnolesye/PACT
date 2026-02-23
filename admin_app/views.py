from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from django.db.models import Q

from admin_app.forms import StudentRegistrationForm, TeacherRegistrationForm
from core_app.models import User, Student, Rights


def admin_right_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not hasattr(user, 'idrights') or user.idrights.rightsname != "Администратор":
            return redirect('search_texts')
        return view_func(request, *args, **kwargs)
    return _wrapped


def generate_password(length=8):
    allowed_chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz234567890'
    return get_random_string(length, allowed_chars=allowed_chars)


@admin_right_required
def admin_index(request):
    return render(request, 'admin_app/index.html')


@admin_right_required
def teachers_list(request):
    q = (request.GET.get('q') or '').strip()

    teachers = (
        User.objects
        .select_related('idrights')
        .filter(idrights__rightsname='Преподаватель')
        .order_by('lastname', 'firstname', 'middlename', 'login')
    )

    if q:
        teachers = teachers.filter(
            Q(login__icontains=q) |
            Q(lastname__icontains=q) |
            Q(firstname__icontains=q) |
            Q(middlename__icontains=q)
        )

    return render(request, 'admin_app/teachers_list.html', {'teachers': teachers, 'q': q})


@admin_right_required
def students_list(request):
    q = (request.GET.get('q') or '').strip()

    students = (
        User.objects
        .select_related('idrights')
        .filter(idrights__rightsname='Студент')
        .order_by('lastname', 'firstname', 'middlename', 'login')
    )

    if q:
        students = students.filter(
            Q(login__icontains=q) |
            Q(lastname__icontains=q) |
            Q(firstname__icontains=q) |
            Q(middlename__icontains=q)
        )

    return render(request, 'admin_app/students_list.html', {'students': students, 'q': q})


@admin_right_required
def reset_user_password(request, iduser: int):
    if request.method != 'POST':
        return redirect('admin_index')

    target_user = get_object_or_404(User, pk=iduser)

    if not hasattr(target_user, 'idrights'):
        messages.error(request, 'У пользователя не определены права.')
        return redirect(request.POST.get('next') or 'admin_index')

    if target_user.idrights.rightsname not in ('Преподаватель', 'Студент'):
        messages.error(request, 'Сброс пароля разрешён только для студентов и преподавателей.')
        return redirect(request.POST.get('next') or 'admin_index')

    raw_password = generate_password(8)
    target_user.set_password(raw_password)
    target_user.save()

    messages.success(request, f'Новый пароль для {target_user.login}: {raw_password}')
    return redirect(request.POST.get('next') or 'admin_index')


@admin_right_required
def register_student(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            login_value = form.cleaned_data['login']

            if User.objects.filter(login=login_value).exists():
                messages.error(request, 'Пользователь с таким логином уже существует')
                return render(request, 'admin_app/register_student.html', {'form': form})

            student_right = Rights.objects.get(rightsname='Студент')
            raw_password = generate_password(8)

            user = User(
                login=login_value,
                lastname=form.cleaned_data['lastname'],
                firstname=form.cleaned_data['firstname'],
                middlename=form.cleaned_data.get('middlename'),
                birthdate=form.cleaned_data.get('birthdate'),
                gender=form.cleaned_data.get('gender'),
                idrights=student_right
            )
            user.set_password(raw_password)
            user.save()

            Student.objects.create(
                iduser=user,
                idgroup=form.cleaned_data['group']
            )

            messages.success(request, f'Студент зарегистрирован. Логин: {user.login} | Пароль: {raw_password}')
            return redirect('admin_students_list')
    else:
        form = StudentRegistrationForm()

    return render(request, 'admin_app/register_student.html', {'form': form})


@admin_right_required
def register_teacher(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            login_value = form.cleaned_data['login']

            if User.objects.filter(login=login_value).exists():
                messages.error(request, 'Пользователь с таким логином уже существует')
                return render(request, 'admin_app/register_teacher.html', {'form': form})

            teacher_right = Rights.objects.get(rightsname='Преподаватель')
            raw_password = generate_password(8)

            user = User(
                login=login_value,
                lastname=form.cleaned_data['lastname'],
                firstname=form.cleaned_data['firstname'],
                middlename=form.cleaned_data.get('middlename'),
                birthdate=form.cleaned_data.get('birthdate'),
                gender=form.cleaned_data.get('gender'),
                idrights=teacher_right
            )
            user.set_password(raw_password)
            user.save()

            messages.success(request, f'Преподаватель зарегистрирован. Логин: {user.login} | Пароль: {raw_password}')
            return redirect('admin_teachers_list')
    else:
        form = TeacherRegistrationForm()

    return render(request, 'admin_app/register_teacher.html', {'form': form})