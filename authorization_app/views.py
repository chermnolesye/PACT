from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .forms import StudentLoginForm, TeacherLoginForm, LoginForm
from core_app.models import User, Student, Rights


def login_student(request):
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            login_data = form.cleaned_data['login']
            password_data = form.cleaned_data['password']
            try:
                user = User.objects.get(login=login_data)
                if user.idrights.rightsname != 'Студент':
                    messages.error(request, 'Этот аккаунт не принадлежит студенту.')
                    return render(request, 'authorization/login_student.html', {'form': form})
            except User.DoesNotExist:
                user = None

            if user and user.check_password(password_data):
                login(request, user)
                messages.success(request, 'Вы успешно вошли в систему как студент.')
                return redirect('search_texts')  # Заменить
            else:
                messages.error(request, 'Неправильный логин или пароль.')
    else:
        form = StudentLoginForm()
    
    return render(request, 'authorization_app/login_student.html', {'form': form})

def login_teacher(request):
    if request.method == 'POST':
        form = TeacherLoginForm(request.POST)
        if form.is_valid():
            login_data = form.cleaned_data['login']
            password_data = form.cleaned_data['password']
            try:
                user = User.objects.get(login=login_data)
                if user.idrights.rightsname != 'Преподаватель':
                    messages.error(request, 'Этот аккаунт не принадлежит преподавателю.')
                    return render(request, 'authorization/login_teacher.html', {'form': form})
            except User.DoesNotExist:
                user = None

            if user and user.check_password(password_data):
                login(request, user)
                messages.success(request, 'Вы успешно вошли в систему как преподаватель.')
                # Получаем ФИО для шапки !!
                fio = f"{user.lastname} {user.firstname} {user.middlename}"
                # Сохраняем ФИО в сессии
                request.session['teacher_fio'] = fio
                return redirect('search_texts')  
            else:
                messages.error(request, 'Неправильный логин или пароль.')
    else:
        form = TeacherLoginForm()
    
    return render(request, 'authorization_app/login_teacher.html', {'form': form})



# --------------

def user_login(request):
    if request.user.is_authenticated:
        if request.user.idrights_id in [2, 4]:
            return redirect('search_texts')
        else:
            return redirect('search_texts') #!!!!

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login_value = form.cleaned_data["login"]
            password_value = form.cleaned_data["password"]
            user = authenticate(request, login=login_value, password=password_value)

            if user is not None:
                login(request, user)
                fio = f"{user.lastname} {user.firstname} {user.middlename or ''}".strip()
                request.session['teacher_fio'] = fio
                
                if user.idrights.idrights in [4]:
                    return redirect('admin_index')

                if user.idrights.idrights in [2]:
                    return redirect('search_texts')
                else:
                    return redirect('search_texts') #!!!!
            else:
                messages.error(request, "Неверный логин или пароль.")
    else:
        form = LoginForm()

    return render(request, "authorization_app/login.html", {"form": form})

def logout_teacher(request):
    logout(request) 
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('login')  
