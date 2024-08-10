from django import template
from sitevars.models import SiteVar

register = template.Library()


@register.simple_tag(takes_context=True)
def sitevar(context, var_name, default=""):
    return context["request"].site.vars.get_value(var_name, default)
