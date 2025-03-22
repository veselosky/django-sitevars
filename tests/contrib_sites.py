"""
Test sitevars with django.contrib.sites installed.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# VAR_DIR = BASE_DIR.joinpath("var")
# VAR_DIR.mkdir(exist_ok=True, parents=True)
# STATIC_ROOT = VAR_DIR.joinpath("static")
# STATIC_ROOT.mkdir(exist_ok=True, parents=True)
STATIC_URL = "/static/"
SITE_ID = 1
SECRET_KEY = "INSECURE! For testing only."
DEBUG = False
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "tests.project"
WSGI_APPLICATION = "tests.project.application"
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "contrib_sites.sqlite3",
    },
}
INSTALLED_APPS = [
    "django_extensions",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "sitevars",
]
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
