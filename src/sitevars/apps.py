from django.apps import AppConfig
from django.apps import apps as global_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, router
from django.db.models.signals import post_migrate
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

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

    def ready(self):
        post_migrate.connect(create_default_site, sender=self)

    @cached_property
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

    @cached_property
    def Site(self):
        """
        Return the Site model class.
        """
        return global_apps.get_model(*self.site_model.split("."))

    def get_site_for_request(self, request):
        """
        Return the Site object for the current request.
        """
        # Check for cached site object on the request
        if hasattr(request, "site"):
            return request.site
        elif hasattr(request, "_sitevars_site"):
            return request._sitevars_site
        elif hasattr(request, "_sitevars_site_id"):
            request._sitevars_site = self.Site.objects.get(pk=request._sitevars_site_id)
            return request._sitevars_site

        # Shortcut if we're using our PlaceholderSite model
        if self.site_model == "sitevars.PlaceholderSite":
            request._sitevars_site = self.Site.objects.get(pk=1)
            request._sitevars_site_id = 1
            return request._sitevars_site

        # If a function is configured, use that to get the site_id
        if hasattr(settings, "CURRENT_SITE_FUNCTION"):
            func = import_string(settings.CURRENT_SITE_FUNCTION)
            request._sitevars_site = func(request)
            request._sitevars_site_id = request._sitevars_site.id
            return request._sitevars_site

        # If a method is configured, use that to get the site_id
        if hasattr(settings, "CURRENT_SITE_METHOD"):
            request._sitevars_site = getattr(self.Site, settings.CURRENT_SITE_METHOD)(
                request
            )
            request._sitevars_site_id = request._sitevars_site.id
            return request._sitevars_site

        # Fallback to the sites framework's get_current() method
        if hasattr(self.Site.objects, "get_current"):
            request._sitevars_site = self.Site.objects.get_current(request)
            request._sitevars_site_id = request._sitevars_site.id
            return request._sitevars_site

        # exhausted all possibilities
        host = request.get_host() if request else "Unknown domain"
        msg = (
            "Unable to identify a site for this request. "
            "Check your settings for SITE_MODEL, CURRENT_SITE_FUNCTION, or "
            "CURRENT_SITE_METHOD configuration."
        )
        raise ImproperlyConfigured(
            msg,
            request,
            host,
        )

    def get_site_id_for_request(self, request):
        """
        Return the site_id for the current request.
        """
        # Shortcut if we're using our PlaceholderSite model
        if self.site_model == "sitevars.PlaceholderSite":
            return 1

        # To save queries, cache site_id on the request object
        if hasattr(request, "_sitevars_site_id"):
            return request._sitevars_site_id

        # Get the site_id
        return self.get_site_for_request(request).id
