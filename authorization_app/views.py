from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm

# --------------

def user_login(request):
    if request.user.is_authenticated:
        if request.user.idrights_id in [2, 4]:
            return redirect('search_texts')
        else:
            return redirect('student_search_texts') #!!!!

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
                    return redirect('student_search_texts') 
            else:
                messages.error(request, "Неверный логин или пароль.")
    else:
        form = LoginForm()

    return render(request, "authorization_app/login.html", {"form": form})

def logout_teacher(request):
    logout(request) 
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('login')  
