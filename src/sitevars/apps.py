from django.apps import AppConfig
from django.conf import settings

# Import the checks module to register system checks
import sitevars.checks  # noqa: F401


class SitevarsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sitevars"

    @property
    def use_cache(self):
        return getattr(settings, "SITEVARS_USE_CACHE", True)
