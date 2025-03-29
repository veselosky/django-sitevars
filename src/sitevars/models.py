import typing as T
from collections.abc import Mapping

from django.apps import apps
from django.db import models
from django.utils.translation import gettext_lazy as _

config = apps.get_app_config("sitevars")


class SiteVarQueryset(models.QuerySet):
    def get_value(self, name: str, default: object = "", asa: T.Callable = str):
        """
        Given a queryset pre-filtered by site, returns the value of the SiteVar with
        the given name. If no value is set for that name, returns the passed default
        value, or empty string if no default was passed.

        To transform the stored string to another type, pass a transform function in
        the ``asa`` argument. If the default value is passed as a string, it will be
        passed to the ``asa`` function for transformation. Exceptions raised by the
        ``asa`` function are propagated, so be prepared to catch them.

        ``None`` is a valid default value for any type, but this function will never
        return ``None`` unless you pass ``None`` as the default. Instead it will call
        ``asa("")``, which may raise exceptions.

        Examples::

            # Returns the string if set, or "" if not set
            x = site.vars.get_value("analytics_id")
            # Returns the string if set, or "Ignore" if not set
            x = site.vars.get_value("abort_retry_ignore", "Ignore")
            # Returns the number of pages as an integer. Raises ValueError if the
            # value is not a number.
            num_items = site.vars.get_value("paginate_by", default=10, asa=int)
            # Booleans may store "false", "0", or "" as false. Anything else is true.
            is_good = site.vars.get_value("is_good", default=False, asa=bool)
            # Parses the value as JSON and returns the result. If you pass default as a
            # string, it will be passed to the asa function for transformation. Here if
            # value is not set, it will return an empty dict.
            data = site.vars.get_value("json_data", "{}", json.loads)
            # If the value is not valid JSON ("" is not!), it will raise JSONDecodeError.
            # This raises JSONDecodeError if not set.
            data = site.vars.get_value("json_data", json.loads)
            # If you pass a non-string as default, it will check that the decoded value
            # is of the same type, or raise a ValueError.
            SiteVar.objects.create(
                site=site, name="json_data", value='{"key": "value"}'
            )
            # Raises ValueError. Expected list, but value decoded to dict.
            site.vars.get_value("json_data", [], json.loads)

        """
        if not callable(asa):
            raise TypeError(f"asa must be a callable, got {type(asa).__name__} instead")
        if not isinstance(name, str):
            raise TypeError(f"name must be a string, got {type(name).__name__} instead")
        if (
            asa is str
            and default is not None  # None is always a valid default value
            and not issubclass(type(default), str)
            and not issubclass(str, type(default))
        ):
            raise TypeError(
                f"default is type {type(default).__name__}, "
                "which is not a type compatible with str. Pass an asa function to convert "
                "a string value to the correct type."
            )

        # First we get the value, which should be a str, then we convert if requested
        try:
            val = self.get(name=name).value
        # Note explicitly NOT catching MultipleObjectsReturned, that's still an error
        except self.model.DoesNotExist:
            val = default

        # If the value is not a str, it's the default they passed. Return it as-is.
        if not isinstance(val, str):
            return val

        # Now we have a string value. Convert it if requested.
        # If the conversion function is str, nothing to do. (But if default is not a
        # str, we need to check for type mismatches below.)
        if asa is str and type(default) is str:
            return val

        # Special case for booleans because bool("false") evaluates to true
        if asa is bool:
            return val.lower() not in ["", "false", "0"]

        rval = asa(val)
        # Sanity check. If they passed a default and asa, the value returned by asa
        # should be a compatible type with the default (i.e. same or subclass). If not,
        # raise a ValueError.
        # Special exception for None, which is a valid default value for any type.
        if (
            default is not None
            and type(default) is not str
            and not issubclass(type(rval), type(default))
            and not issubclass(type(default), type(rval))
        ):
            # If the conversion function returned a type incompatible with the default,
            # raise a ValueError
            raise ValueError(
                f"Type mismatch: default has type {type(default).__name__} "
                f"but asa function {asa} returned type {type(rval).__name__}"
            )
        return rval

    def get_multiple_values(
        self,
        names: T.Optional[T.List[str]] = None,
        *,
        defaults: T.Optional[T.Mapping] = None,
        asa: T.Union[T.Callable, T.Mapping] = str,
    ) -> T.Dict[str, object]:
        """
        Given a queryset pre-filtered by site, returns a dictionary mapping
        the given SiteVar names to their vaues. If no names are given, returns ALL
        SiteVars for the site.

        Default values for each name may be passed as a mapping (dict) in the
        ``defaults`` argument.

        If ``asa`` is a callable, it will be used to convert each value to the correct
        type. If ``asa`` is a mapping, it will be used to look up a conversion function
        by the SiteVar name. The mapping should be a dictionary mapping the name of the
        SiteVar to the conversion function to use. Any name not found in the mapping
        will be returned as a string.

        The values will be fetched from the database in a single query, so if you need
        to access multiple SiteVars in the same scope, this will be more efficient than
        calling ``get_value`` multiple times.
        """
        if defaults is None:
            defaults = {}
        if names is None:
            names = []
        if not issubclass(type(defaults), Mapping):
            raise TypeError(
                f"defaults must be a mapping, got {type(defaults).__name__} instead"
            )
        if not callable(asa) and not issubclass(type(asa), Mapping):
            raise TypeError(
                f"asa must be a callable or a mapping, got {type(asa).__name__} instead"
            )

        # Get the values from the database
        if not names:
            # If no names were passed, get all SiteVars for the site
            qs = self.all()
        else:
            qs = self.filter(name__in=names)

        if callable(asa) and asa is not str:
            vals = {var.name: asa(var.value) for var in qs}
        else:
            vals = {var.name: var.value for var in qs}

        # Fill in any missing values
        for name in names:
            if name not in vals:
                if callable(asa) and asa is not str:
                    vals[name] = asa(defaults.get(name, ""))
                else:
                    vals[name] = defaults.get(name, "")

        # If asa is a mapping, convert each value using the mapping
        if isinstance(asa, Mapping):
            for name in asa:
                if name in vals and issubclass(type(vals[name]), str):
                    vals[name] = asa[name](vals[name])

        return vals


class SiteVar(models.Model):
    """
    Site-specific variables are stored here. All site variable are injected into
    template contexts using the context processor in
    ``sitevars.context_processors.inject_sitevars``.
    """

    site = models.ForeignKey(
        config.site_model,
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
        if config.site_model == "sitevars.PlaceholderSite":
            return f"{self.name}={self.value}"
        elif hasattr(self.site, "domain"):
            return f"{self.name}={self.value} ({self.site.domain})"
        else:
            return f"{self.name}={self.value} ({self.site})"


class PlaceholderSite(models.Model):
    """
    A placeholder site model to use when the Django's Site model is not available.
    """

    domain = models.CharField(_("domain name"), max_length=100, blank=True)
    name = models.CharField(_("display name"), max_length=50, blank=True)

    def __str__(self):
        return "Placeholder Site"
