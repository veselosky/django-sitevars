from django.apps import apps
from django.core.cache import cache


# A context processor to add our vars to template contexts:
def inject_sitevars(request):
    """Add all sitevars to the template context."""
    conf = apps.get_app_config("sitevars")
    SiteVar = conf.get_model("SiteVar")

    # Get the site_id, or raise ImproperlConfigured
    site_id = conf.get_site_id_for_request(request)

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
