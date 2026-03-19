from django.shortcuts import render, redirect
from django.urls import reverse

def corpus_search(request):
    return render(request, 'corpus_search.html')