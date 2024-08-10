from django.apps import apps
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache


# A context processor to add our vars to template contexts:
def inject_sitevars(request):
    """Add all sitevars to the template context."""
    conf = apps.get_app_config("sitevars")
    SiteVar = conf.get_model("SiteVar")

    if hasattr(request, "site"):
        # If site middleware is installed, we save a query
        site = request.site
    else:
        site = get_current_site(request)
    qs = SiteVar.objects.filter(site_id=site.id)

    if not conf.use_cache:
        return {var.name: var.value for var in qs}

    # Construct the cache key and retrieve the cached value
    key = f"sitevars:{site.id}"
    allvars = cache.get(key, None)
    if allvars is None:
        # Empty cache, populate the cache
        allvars = {var.name: var.value for var in qs}
        cache.set(key, allvars)
    return allvars
