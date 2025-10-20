from django.shortcuts import render

# Create your views here.

def teacher_exercise(request):

    return render(request, "teacher_exercise.html")