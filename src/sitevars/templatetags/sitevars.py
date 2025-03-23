from django import template
from django.apps import apps

register = template.Library()
config = apps.get_app_config("sitevars")


@register.simple_tag(takes_context=True)
def sitevar(context, var_name, default=""):
    """
    Inserts the value of a site variable for the current site.

    Usage::

        {% load sitevars %}
        {% sitevar "my_var" %}
        {% sitevar "my_var" "default" %}

    Note: If you are using the ``sitevars.context_processors.inject_sitevars``
    context processor, you can access site variables directly in templates. ::

        {{ my_var|default:"default" }}

    """
    SiteVar = config.get_model("SiteVar")

    # Shortcut when using PlaceholderSite
    if config.site_model.lower() == "sitevars.placeholdersite":
        return SiteVar.objects.get_value(var_name, default)

    # Get the site_id for the current site
    site_id: int = 0

    # Using site middleware?
    request = context.get("request")
    if request and hasattr(request, "site") and hasattr(request.site, "id"):
        site_id = request.site.id

    # Using a sites framework without the middleware?
    if not site_id:
        Site = apps.get_model(*config.site_model.split("."))
        if hasattr(Site.objects, "get_current"):
            site_id = Site.objects.get_current(request).id

    return SiteVar.objects.filter(site_id=site_id).get_value(var_name, default)
