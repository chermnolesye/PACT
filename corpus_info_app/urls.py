from django.urls import path
from .views import corpus_size_api
from django.views.generic import TemplateView

urlpatterns = [
    path("api/corpus-size/", corpus_size_api, name="corpus_size_api"),
]