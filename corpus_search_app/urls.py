from django.urls import path
from .views import (
    corpus_search,
    corpus_filters_api,
    corpus_search_api,
    corpus_text_detail
)

urlpatterns = [
    path("", corpus_search, name="corpus_search"),
    path("api/filters/", corpus_filters_api, name="corpus_filters_api"),
    path("api/search/", corpus_search_api, name="corpus_search_api"),
    path("text/<int:text_id>/", corpus_text_detail, name="corpus_text_detail"),
]