from django.conf import settings

def language_context(request):
    return {
        'pact_language_name': settings.PACT_LANGUAGE_NAME,
    }