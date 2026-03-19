from django.urls import path
from . import views

urlpatterns = [
    path('corpus_search/', views.corpus_search, name = 'corpus_search'),
]
