from django.core.checks import Tags, Warning, register


@register(Tags.admin)
def check_contrib_sites_comes_before_sitevars(app_configs, **kwargs):
    """
    Checks that contrib.sites is installed before sitevars. If it's not, the admin
    registration will fail and the SiteAdmin will not have the sitevars inlines.
    """
    from django.conf import settings

    if (
        "sitevars" in settings.INSTALLED_APPS
        and "django.contrib.sites" in settings.INSTALLED_APPS
    ):
        sitevars_index = settings.INSTALLED_APPS.index("sitevars")
        sites_index = settings.INSTALLED_APPS.index("django.contrib.sites")
        if sitevars_index < sites_index:
            return [
                Warning(
                    "sitevars is installed before django.contrib.sites",
                    hint=(
                        "contrib.sites must be installed before sitevars in INSTALLED_APPS "
                        "to ensure SiteVars are editable in the SiteAdmin."
                    ),
                    id="sitevars.W001",
                    obj="sitevars",
                )
            ]
    return []


@register(Tags.sites)
def check_request_context_processor_is_installed(app_configs, **kwargs):
    """
    Checks that the ``request`` context processor is installed, because the sitevar
    template tag requires it.
    """
    from django.conf import settings

    using_context_processor = False
    for backend in settings.TEMPLATES:
        if "django.template.context_processors.request" in backend.get(
            "OPTIONS", {}
        ).get("context_processors", []):
            using_context_processor = True
            break

    if not using_context_processor:
        return [
            Warning(
                "'django.template.context_processors.request' must be enabled in "
                "DjangoTemplates (TEMPLATES) in order to use the sitevar template tag.",
                id="sitevars.W002",
                obj="sitevars",
            )
        ]
    return []
