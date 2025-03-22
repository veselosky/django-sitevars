from django import template

register = template.Library()


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
    return context["request"].site.vars.get_value(var_name, default)
