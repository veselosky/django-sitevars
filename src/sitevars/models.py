import typing as T

from django.apps import apps
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class SiteVarQueryset(models.QuerySet):
    def get_value(self, name: str, default: str = "", asa: T.Callable = str):
        """
        Given a queryset pre-filtered by site, returns the value of the SiteVar with
        the given name. If no value is set for that name, returns the passed default
        value, or empty string if no default was passed. To transform the stored string
        to another type, pass a transform function in the asa argument. The default
        value should be passed as a string; it will be passed to the asa function
        for transformation.

        Examples:

        # Returns the string if set, or "" if not set
        x = site.vars.get_value("analytics_id")
        # Returns the string if set, or "Ignore" if not set
        x = site.vars.get_value("abort_retry_ignore", "Ignore")
        # Returns the number of pages as an integer. Note the default should be a str.
        num_items = site.vars.get_value("paginate_by", default="10", asa=int)
        # Parses the value as JSON and returns the result
        data = site.vars.get_value("json_data", "{}", json.loads)
        """
        conf = apps.get_app_config("sitevars")
        # Determine the site ID from the queryset
        site_id = None
        for lookup in self.query.where.children:
            if not isinstance(lookup, models.fields.related_lookups.RelatedExact):
                continue
            if lookup.lhs.target.name == "site":
                site_id = lookup.rhs
                break
        if site_id is None:
            raise ValueError("get_value requires a queryset filtered by site")

        if conf.use_cache:
            # Construct the cache key and retrieve the cached value
            key = f"sitevars:{site_id}"
            allvars = cache.get(key, None)
            if allvars is None:
                # Empty cache, populate the cache
                allvars = {var.name: var.value for var in self.all()}
                cache.set(key, allvars)
            val = allvars.get(name, default)
            return asa(val) if val is not None else val

        # No cache, just query the DB
        try:
            return asa(self.get(name=name).value)
        except self.model.DoesNotExist:
            # This allows None as a default, without crashing on e.g. `int(None)`
            return asa(default) if default is not None else default
        # Note explicitly NOT catching MultipleObjectsReturned, that's still an error

    def clear_cache(self, site_id: T.Optional[int] = None):
        """
        Clear the cache for the given site_id, or all sites if no site_id is given.
        """
        if site_id is not None:
            key = f"sitevars:{site_id}"
            cache.delete(key)
        else:
            for site in Site.objects.all():
                key = f"sitevars:{site.pk}"
                cache.delete(key)


class SiteVar(models.Model):
    """
    Site-specific variables are stored here. All site variable are injected into
    template contexts using the context processor in
    ``sitevars.context_processors.inject_sitevars``.
    """

    site = models.ForeignKey(
        "sites.Site",
        verbose_name=_("site"),
        on_delete=models.CASCADE,
        related_name="vars",
    )
    name = models.CharField(_("name"), max_length=100)
    value = models.TextField(_("value"))

    objects = SiteVarQueryset.as_manager()

    class Meta:
        base_manager_name = "objects"
        unique_together = ("site", "name")
        verbose_name = _("site variable")
        verbose_name_plural = _("site variables")

    def __str__(self):
        return f"{self.name}={self.value} ({self.site.domain})"

    def save(self, *args, **kwargs):
        # Clear the cache if it exists
        transaction.on_commit(lambda: self.objects.clear_cache(self.site.id))
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Clear the cache if it exists
        transaction.on_commit(lambda: self.objects.clear_cache(self.site.id))
        return super().delete(*args, **kwargs)
