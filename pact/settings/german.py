"""
German settings for pact project.
"""

from .base import *

USE_WSL_FOR_RFTAGGER = True
RFTAGGER_PATH = "/home/chermnolesye/rftagger/RFTagger"
RFTAGGER_LANGUAGE = "german"

PACT_LANGUAGE_NAME = "Deutsche"
NLTK_LANGUAGE = "german"
PROJECT_LANGUAGE_CODE = "de"


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