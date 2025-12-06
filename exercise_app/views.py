from django.shortcuts import render

# Create your views here.

def teacher_exercise(request):

    return render(request, "teacher_exercise.html")

def review_student(request):
    return render(request, "review_student.html")