import logging

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django import forms

from sitevars.models import SiteVar, PlaceholderSite

logger = logging.getLogger("sitevars")


# These admin classes are for use with django.contrib.sites.
class SiteVarInline(admin.TabularInline):
    extra: int = 1
    model = SiteVar


class ContribSiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "name")
    search_fields = ("domain", "name")
    inlines = [SiteVarInline]


# This class should be usable with any sites framework.
class SiteVarAdmin(admin.ModelAdmin):
    list_display = ("name", "value", "site")
    list_filter = ("site",)
    list_editable = ("value",)
    search_fields = ("name", "value")
    ordering = ("site", "name")


# This form and admin class are used only when using the PlaceholderSite model.
class PlaceholderSiteVarAdminForm(forms.ModelForm):
    class Meta:
        model = SiteVar
        fields = ["site", "name", "value"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check if we're using the PlaceholderSite model
        model = apps.get_app_config("sitevars").site_model
        if model.lower() == "sitevars.placeholdersite":
            # Hide the site field and set default to PlaceholderSite with id=1
            self.fields["site"].widget = forms.HiddenInput()
            # Should have been created at migration time, but JIC
            self.initial["site"] = PlaceholderSite.objects.get_or_create(id=1)[0]


class PlaceholderSiteVarAdmin(admin.ModelAdmin):
    form = PlaceholderSiteVarAdminForm
    list_display = ("name", "value")
    list_editable = ("value",)
    search_fields = ("name", "value")
    ordering = ("name",)


if "django.contrib.sites" in settings.INSTALLED_APPS:
    # Note: if this raises admin.NotRegistered, that means contrib.sites is not installed,
    # or is installed after sitevars. Trying to register our SiteAdmin would cause a crash.
    try:
        # Unregister the default SiteAdmin and register our ContribSiteAdmin
        from django.contrib.sites.models import Site

        admin.sites.site.unregister(Site)
        admin.site.register(Site, ContribSiteAdmin)
        admin.site.register(SiteVar, SiteVarAdmin)

    except admin.exceptions.NotRegistered:
        logger.warning(
            "SiteAdmin was not registered. "
            "Place sitevars AFTER contrib.sites in INSTALLED_APPS."
        )
        pass

elif apps.get_app_config("sitevars").site_model.lower() == "sitevars.placeholdersite":
    # If we're using the PlaceholderSite model, register the PlaceholderSiteVarAdmin
    admin.site.register(SiteVar, PlaceholderSiteVarAdmin)

else:
    admin.site.register(SiteVar, SiteVarAdmin)
