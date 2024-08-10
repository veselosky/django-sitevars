import logging
from django.contrib import admin
from django.contrib.sites.models import Site

from sitevars.models import SiteVar

logger = logging.getLogger("sitevars")

# Note: if this raises admin.NotRegistered, that means contrib.sites is not installed,
# or is installed after sitevars. Trying to register our SiteAdmin would cause a crash.
try:
    admin.sites.site.unregister(Site)

    class SiteVarInline(admin.TabularInline):
        extra: int = 1
        model = SiteVar

    @admin.register(Site)
    class SiteAdmin(admin.ModelAdmin):
        list_display = ("domain", "name")
        search_fields = ("domain", "name")
        inlines = [SiteVarInline]

except admin.exceptions.NotRegistered:
    logger.warning("SiteAdmin was not registered.")
    pass


@admin.register(SiteVar)
class SiteVarAdmin(admin.ModelAdmin):
    list_display = ("name", "value", "site")
    list_filter = ("site",)
