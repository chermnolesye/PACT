from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# NLTK
NLTK_DATA = os.path.join(BASE_DIR, "nltk_data")
os.environ["NLTK_DATA"] = NLTK_DATA

SECRET_KEY = "django-insecure-$1rz*q6a2pfc(yzba@9fw146p8ono9^en#o-jqwji@n*!@#l%@"

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
    "core_app",
    "authorization_app",
    "text_app",
    "students_app",
    "years_and_groups_app",
    "statistics_app",
    "exercise_app",
    "admin_app",
    "corpus_search_app",
]

AUTH_USER_MODEL = "core_app.User"

AUTHENTICATION_BACKENDS = [
    "authorization_app.backends.LegacyAndDjangoBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
]

ROOT_URLCONF = "pact.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "text_app/templates/text_app",
            BASE_DIR / "students_app/templates/students_app",
            BASE_DIR / "years_and_groups_app/templates/years_and_groups_app",
            BASE_DIR / "exercise_app/templates/exercise_app",
            BASE_DIR / "corpus_search_app/templates/corpus_search_app",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pact.context_processors.language_context",
            ],
        },
    },
]

WSGI_APPLICATION = "pact.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "pactgerman",
        "USER": "root",
        "PASSWORD": "12345",
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
            "collation": "utf8mb4_general_ci",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------

PACT_LANGUAGE_NAME = ""
NLTK_LANGUAGE = ""
PROJECT_LANGUAGE_CODE = ""


POS_TAGGER_BACKEND = ""
POS_TAGSET = ""

# RFTagger
USE_WSL_FOR_RFTAGGER = True
RFTAGGER_PATH = "/home/chermnolesye/rftagger/RFTagger"
RFTAGGER_LANGUAGE = ""

# CoreNLP
CORENLP_URL = "http://localhost:9000"
CORENLP_LANGUAGE = ""
CORENLP_ANNOTATORS = "tokenize,ssplit,pos"

try:
    from .nltk_setup import download_nltk_resources
    download_nltk_resources()
except Exception:
    pass