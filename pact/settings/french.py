from .base import *

PACT_LANGUAGE_NAME = "Français"
NLTK_LANGUAGE = "french"
PROJECT_LANGUAGE_CODE = "fr"

POS_TAGGER_BACKEND = "corenlp"
POS_TAGSET = "treebank"

CORENLP_URL = "http://localhost:9000"
CORENLP_LANGUAGE = "french"
CORENLP_ANNOTATORS = "tokenize,ssplit,pos"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "pactfrench",
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