from django.conf import settings

def language_context(request):
    language_label_in_russian = "Немецком"

    if getattr(settings, "PROJECT_LANGUAGE_CODE", "de") == "fr":
        language_label_in_russian = "Французском"

    return {
        'pact_language_name': settings.PACT_LANGUAGE_NAME,
        'language_label_in_russian': language_label_in_russian,
    }