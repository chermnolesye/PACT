from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from authorization_app.views import user_login
from django.views.generic.base import RedirectView

urlpatterns = [
    path("login/", user_login, name="user_login"),
    path('admin/', admin.site.urls),
    path('auth/', include('authorization_app.urls')),
    path('text/', include('text_app.urls')),
    path('students/', include('students_app.urls')),
    path('years_groups/', include('years_and_groups_app.urls')),
    path('statistics/', include('statistics_app.urls')),
    path('exercise/', include('exercise_app.urls')),
    path('admin-panel/', include("admin_app.urls")),
    path("", include("corpus_info_app.urls")),
    path('', RedirectView.as_view(url='https://pact.ai.petrsu.ru/')),
    path('corpus/', include("corpus_search_app.urls"))
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
