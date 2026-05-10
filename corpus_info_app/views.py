from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from core_app.models import Token, ErrorTag


def home_page(request):
    if not request.user.is_authenticated:
        base_template = "guest_base.html"
    else:
        if hasattr(request.user, "idrights"):
            if request.user.idrights.idrights == 2:
                base_template = "base.html"
            elif request.user.idrights.idrights == 1:
                base_template = "student_base.html"
            elif request.user.idrights.idrights == 4:
                base_template = "admin_base.html"
            else:
                base_template = "guest_base.html"
        else:
            base_template = "guest_base.html"

    return render(request, "corpus_info_app/home.html", {
        "project_name": "ПАКТ",
        "german_api_url": settings.CORPUS_INFO_URLS["german"]["api"],
        "french_api_url": settings.CORPUS_INFO_URLS["french"]["api"],
        "german_login_url": settings.CORPUS_INFO_URLS["german"]["login"],
        "french_login_url": settings.CORPUS_INFO_URLS["french"]["login"],
        "base_template": base_template,
    })


def corpus_size_api(request):
    token_count = Token.objects.exclude(tokentext='-EMPTY-').count()
    error_tags_count = ErrorTag.objects.count()

    return JsonResponse({
        "project_version": getattr(settings, "PACT_PROJECT_VERSION", ""),
        "language_name": getattr(settings, "PACT_LANGUAGE_NAME", ""),
        "language_code": getattr(settings, "PROJECT_LANGUAGE_CODE", ""),
        "token_count": token_count,
        "error_tags_count": error_tags_count,
        "updated_at": timezone.localtime().strftime("%d.%m.%Y %H:%M"),
    })
