from django.urls import path
from .views import user_login, logout_teacher

urlpatterns = [
    path('login/', user_login, name = 'login'),
    path('logout/', logout_teacher, name = 'logout'),
]
