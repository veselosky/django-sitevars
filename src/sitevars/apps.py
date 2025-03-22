from django.apps import AppConfig
from django.apps import apps as global_apps
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, router
from django.db.models.signals import post_migrate

# Import the checks module to register system checks
import sitevars.checks  # noqa: F401


def create_default_site(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    """
    Create the default singleton PlaceholderSite object.
    """
    # If the model doesn't exist, this is a legacy installation using
    # django.contrib.sites upgraded from 1.x. Nothing to do, we won't need the
    # PlaceholderSite.
    try:
        Site = apps.get_model("sitevars", "PlaceholderSite")
    except LookupError:
        return

    if not router.allow_migrate_model(using, Site):
        return

    # If the table is empty, create the default site
    if not Site.objects.using(using).exists():
        Site(pk=1, domain="example.com", name="example.com").save(using=using)


class SitevarsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sitevars"

    @property
    def use_cache(self):
        return getattr(settings, "SITEVARS_USE_CACHE", True)

    @property
    def site_model(self):
        """
        Return the name of the Site model to use for foreign keys.
        """
        name = getattr(settings, "SITE_MODEL", None)
        if not name and "django.contrib.sites" in settings.INSTALLED_APPS:
            name = "sites.Site"
        if not name:
            name = "sitevars.PlaceholderSite"
        return name

    def ready(self):
        post_migrate.connect(create_default_site, sender=self)
