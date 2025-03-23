import logging
from django.apps import apps
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


# A context processor to add our vars to template contexts:
def inject_sitevars(request):
    """Add all sitevars to the template context."""
    conf = apps.get_app_config("sitevars")
    site_model = conf.site_model.lower()
    SiteVar = conf.get_model("SiteVar")
    Site = apps.get_model(*site_model.split("."))

    # Get the site_id
    site_id: int = 0
    # First check if a middlware has set the site attribute on the request. This is the
    # recommended way to get the site object.
    if hasattr(request, "site") and hasattr(request.site, "id"):
        # If site middleware is installed, we save a query
        logger.debug("Using request.site.id")
        site_id = request.site.id

    # Failing that, see if we are using our own PlaceholderSite model
    if not site_id and site_model == "sitevars.placeholdersite":
        # There's only ever one PlaceholderSite, always pk=1
        logger.debug("Using PlaceholderSite 1")
        site_id = 1

    # We must be using a sites framework without a middleware. Could be Django's or
    # something else. Last resort, see if it implements the Site.objects.get_current()
    # method like Django's does.
    if not site_id and hasattr(Site.objects, "get_current"):
        # Could raise a Site.DoesNotExist, that's fine.
        logger.debug("Using Site.objects.get_current()")
        site_id = Site.objects.get_current(request).id

    # If we still don't have a site_id, we can't proceed
    if not site_id:
        raise ImproperlyConfigured(
            "Unable to identify a site from request domain. ",
            request.get_host(),
        )

    qs = SiteVar.objects.filter(site_id=site_id)

    if not conf.use_cache:
        return {var.name: var.value for var in qs}

    # Construct the cache key and retrieve the cached value
    key = f"sitevars:{site_id}"
    allvars = cache.get(key, None)
    if allvars is None:
        # Empty cache, populate the cache
        allvars = {var.name: var.value for var in qs}
        cache.set(key, allvars)
    return allvars
