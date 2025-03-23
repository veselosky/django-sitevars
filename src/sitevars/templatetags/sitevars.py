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

    # Shortcut when using PlaceholderSite, don't even need the request
    if config.site_model.lower() == "sitevars.placeholdersite":
        return SiteVar.objects.get_value(var_name, default)

    # Get the site_id for the current site
    site_id = config.get_site_id_for_request(context["request"])

    return SiteVar.objects.filter(site_id=site_id).get_value(var_name, default)
