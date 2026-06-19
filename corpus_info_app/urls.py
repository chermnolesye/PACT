from django.urls import path
from .views import home_page, corpus_size_api

urlpatterns = [
    path("api/corpus-size/", corpus_size_api, name="corpus_size_api"),
]