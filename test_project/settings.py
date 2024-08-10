#! /usr/bin/env python
import os
from pathlib import Path


DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32))
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

BASE_DIR = Path(__file__).resolve().parent.parent
VAR_DIR = BASE_DIR.joinpath("var")
VAR_DIR.mkdir(exist_ok=True, parents=True)
STATIC_ROOT = VAR_DIR.joinpath("static")
STATIC_ROOT.mkdir(exist_ok=True, parents=True)

SITE_ID = 1
ROOT_URLCONF = "test_project.urls"
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": VAR_DIR / "db.sqlite3",
    },
}
INSTALLED_APPS = [
    "django_extensions",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "sitevars",
]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"": {"handlers": ["console"], "level": "INFO"}},
}
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
STATIC_URL = "static/"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "LOCATION": VAR_DIR / "media",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        "LOCATION": STATIC_ROOT,
    },
}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.messages.context_processors.messages",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
            ]
        },
    }
]
USE_TZ = True
WSGI_APPLICATION = "test_project.wsgi.application"
