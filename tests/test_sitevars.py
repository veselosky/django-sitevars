import json
from unittest import skipIf
from unittest.mock import Mock

from django.apps import apps
from django.contrib.admin import site as adminsite
from django.contrib.auth.models import User
from django.core.checks import Warning
from django.db.utils import IntegrityError
from django.template import Context, Template
from django.test import TestCase, override_settings, RequestFactory
from django.urls import reverse

from sitevars import checks
from sitevars.context_processors import inject_sitevars
from sitevars.models import SiteVar

config = apps.get_app_config("sitevars")


class AdminSmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create(
            username="test_admin",
            password="super-secure",
            is_staff=True,
            is_superuser=True,
        )
        return super().setUpTestData()

    def test_load_admin_pages(self):
        """Load each admin change and add page to check syntax in the admin classes."""
        self.client.force_login(self.user)

        app_label = "sitevars"
        app = apps.get_app_config(app_label)
        for model in app.get_models():
            if not adminsite.is_registered(model):
                continue

            with self.subTest(model=model):
                changelist_url = reverse(
                    f"admin:{app_label}_{model._meta.model_name}_changelist"
                )
                add_url = reverse(f"admin:{app_label}_{model._meta.model_name}_add")
                resp_changelist = self.client.get(changelist_url)
                resp_add = self.client.get(add_url)
                self.assertEqual(resp_changelist.status_code, 200)
                self.assertEqual(resp_add.status_code, 200)


class AppConfigTest(TestCase):
    @skipIf(
        config.site_model != "sitevars.PlaceholderSite",
        "Test only applies to PlaceholderSite model.",
    )
    def test_get_site_id_for_request__placeholder_site(self):
        """Test the get_site_id_for_request method."""
        request = RequestFactory().get("/")
        self.assertEqual(config.get_site_id_for_request(request), 1)

    @skipIf(
        config.site_model == "sitevars.PlaceholderSite",
        "Not used with PlaceholderSite model.",
    )
    def test_get_site_id_for_request__site_middleware(self):
        """Test the get_site_id_for_request when request.site is valid."""
        request = RequestFactory().get("/")
        request.site = Mock()
        request.site.id = 7
        self.assertEqual(config.get_site_id_for_request(request), 7)

    @skipIf(
        config.site_model != "tests.FakeSite",
        "Only applies to custom SITE_MODEL.",
    )
    def test_get_site_id_for_request__current_site_function(self):
        """Test the get_site_id_for_request when CURRENT_SITE_FUNCTION is set."""
        with override_settings(CURRENT_SITE_FUNCTION="tests.models.get_current_site"):
            request = RequestFactory().get("/")
            with self.assertLogs("sitevars.testing", "INFO") as cm:
                self.assertEqual(config.get_site_id_for_request(request), 1)
            self.assertIn("INFO:sitevars.testing:get_current_site() called", cm.output)

    @skipIf(
        config.site_model != "tests.FakeSite",
        "Only applies to custom SITE_MODEL.",
    )
    def test_get_site_id_for_request__current_site_method(self):
        """Test the get_site_id_for_request when CURRENT_SITE_METHOD is set."""
        with override_settings(CURRENT_SITE_METHOD="get_current"):
            request = RequestFactory().get("/")
            with self.assertLogs("sitevars.testing", "INFO") as cm:
                self.assertEqual(config.get_site_id_for_request(request), 1)
            self.assertIn(
                "INFO:sitevars.testing:FakeSite.get_current() called", cm.output
            )

    @skipIf(
        config.site_model != "tests.FakeSite",
        "Only applies to contrib.sites or compatible.",
    )
    def test_get_site_id_for_request__fallback_to_get_current(self):
        """Test that it falls back to Site.objects.get_current"""
        request = RequestFactory().get("/")
        with self.assertLogs("sitevars.testing", "INFO") as cm:
            self.assertEqual(config.get_site_id_for_request(request), 1)
        self.assertEqual(
            cm.output, ["INFO:sitevars.testing:FakeSiteManager.get_current() called"]
        )


class ContextProcessorTest(TestCase):
    def test_context_processor_returns_dict_with_one_query(self):
        """Test the context processor "happy path"."""
        # Create a sitevar
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")

        request = RequestFactory().get("/")
        # Simulate site middleware
        request.site = Mock()
        request.site.id = 1
        with self.assertNumQueries(1):
            context = inject_sitevars(request)
        self.assertEqual(context, {"testvar": "testvalue"})

    def test_context_processor_returns_dict__without_site_middleware(self):
        """Test the context processor when sites middleware not installed."""
        # Create a sitevar
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")

        # Test the context processor returns the sitevar
        request = RequestFactory().get("/")
        assert not hasattr(request, "site")

        context = inject_sitevars(request)

        self.assertEqual(context, {"testvar": "testvalue"})


class SiteVarModelTest(TestCase):
    def test_sitevar_str(self):
        """Test the string representation of a sitevar."""
        sitevar = SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        if config.site_model == "sitevars.PlaceholderSite":
            self.assertEqual(str(sitevar), "testvar=testvalue")
        elif hasattr(sitevar.site, "domain"):
            self.assertEqual(str(sitevar), "testvar=testvalue (example.com)")

    def test_sitevar_unique_together(self):
        """Test that sitevar names are unique per site."""
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        with self.assertRaises(IntegrityError):
            SiteVar.objects.create(site_id=1, name="testvar", value="othervalue")

    @skipIf(
        config.site_model.lower() == "sitevars.placeholdersite",
        "Test does not apply when using PlaceholderSite model.",
    )
    def test_sitevar_unique_together_different_sites(self):
        """Test that sitevar names are not unique across different sites."""
        site1 = config.Site.objects.get(pk=1)
        site2 = config.Site.objects.create(domain="example2.com", name="example2.com")
        SiteVar.objects.create(site=site1, name="testvar", value="testvalue")
        SiteVar.objects.create(site=site2, name="testvar", value="othervalue")
        self.assertEqual(
            SiteVar.objects.filter(site=site2).get_value("testvar"), "othervalue"
        )
        self.assertEqual(
            SiteVar.objects.filter(site=site1).get_value("testvar"), "testvalue"
        )

    @skipIf(
        config.site_model.lower() != "sitevars.placeholdersite",
        "Test only applies to PlaceholderSite model.",
    )
    def test_get_value_placeholder_site(self):
        """Test that get_value automatically filters queries when using the placeholder site."""
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        with self.assertNumQueries(1):
            self.assertEqual(SiteVar.objects.get_value("testvar"), "testvalue")

    def test_get_value_asa(self):
        """Test that get_value works with the asa argument."""
        site = config.Site.objects.get(pk=1)

        # Missing values return ""
        self.assertEqual(site.vars.get_value("testvar"), "")

        # Defaults of type str should be converted with asa
        self.assertEqual(site.vars.get_value("testvar", default="1", asa=int), 1)
        self.assertEqual(site.vars.get_value("testvar", default="1.0", asa=float), 1.0)
        self.assertEqual(site.vars.get_value("testvar", default="True", asa=bool), True)
        self.assertEqual(
            site.vars.get_value("testvar", default="False", asa=bool), False
        )
        # Default value should be returned unchanged if not a str
        self.assertEqual(site.vars.get_value("testvar", default=1, asa=int), 1)
        self.assertEqual(site.vars.get_value("testvar", default=1.0, asa=float), 1.0)
        self.assertEqual(site.vars.get_value("testvar", default=True, asa=bool), True)
        self.assertEqual(site.vars.get_value("testvar", default=False, asa=bool), False)
        # If the default is None, it should be returned as-is, with or without asa
        self.assertEqual(site.vars.get_value("testvar", default=None, asa=int), None)
        self.assertEqual(site.vars.get_value("testvar", default=None, asa=float), None)
        self.assertEqual(site.vars.get_value("testvar", default=None, asa=bool), None)
        self.assertEqual(site.vars.get_value("testvar", default=None), None)
        # If the default is not a string, it should be returned as-is (even if it's
        # wrong) because we have no sure way of knowing what asa would return.
        self.assertEqual(site.vars.get_value("testvar", default=1, asa=float), 1)

        # If a default of a non-string type is passed with no asa, raise TypeError,
        # as this would cause a type mismatch if the value were set.
        with self.assertRaises(TypeError):
            site.vars.get_value("testvar", default=1)
        with self.assertRaises(TypeError):
            site.vars.get_value("testvar", default=1.0)
        with self.assertRaises(TypeError):
            site.vars.get_value("testvar", default=True)
        with self.assertRaises(TypeError):
            site.vars.get_value("testvar", default=False)
        with self.assertRaises(TypeError):
            site.vars.get_value("testvar", default={})

        # If no default is provided, calls asa("") which could raise errors.
        # Note that bool would return False, see the separate test_get_value_asa_bool
        with self.assertRaises(ValueError):
            site.vars.get_value("testvar", asa=int)
        with self.assertRaises(ValueError):
            site.vars.get_value("testvar", asa=float)
        with self.assertRaises(json.JSONDecodeError):
            site.vars.get_value("testvar", asa=json.loads)

        # Done with defaults, test with stored values
        SiteVar.objects.create(site_id=1, name="testvar", value="123")

        # With no asa, you get a string
        self.assertEqual(site.vars.get_value("testvar"), "123")
        # With asa, you get the converted value
        self.assertEqual(site.vars.get_value("testvar", asa=int), 123)
        self.assertEqual(site.vars.get_value("testvar", asa=str), "123")
        self.assertEqual(site.vars.get_value("testvar", asa=bool), True)
        self.assertEqual(site.vars.get_value("testvar", asa=float), 123.0)
        self.assertEqual(site.vars.get_value("testvar", default=None), "123")
        # If you pass a non-callable asa, raise a TypeError
        with self.assertRaises(TypeError):
            site.vars.get_value("testvar", asa="not callable")
        # If you pass a default that is not the same type as the value, raise a ValueError
        with self.assertRaises(ValueError):
            site.vars.get_value("testvar", asa=int, default={})

    def test_get_value_asa_bool(self):
        """Test that get_value works with the asa argument for boolean values.
        Any value other than "false", "0", or "" is considered True.
        """
        site = config.Site.objects.get(pk=1)

        self.assertEqual(site.vars.get_value("testvar"), "")
        self.assertEqual(site.vars.get_value("testvar", asa=bool), False)
        self.assertEqual(site.vars.get_value("testvar", default="True", asa=bool), True)
        self.assertEqual(site.vars.get_value("testvar", default=True, asa=bool), True)
        self.assertEqual(
            site.vars.get_value("testvar", default="False", asa=bool), False
        )
        self.assertEqual(site.vars.get_value("testvar", default=False, asa=bool), False)
        self.assertEqual(site.vars.get_value("testvar", default="0", asa=bool), False)
        self.assertEqual(site.vars.get_value("testvar", default="1", asa=bool), True)
        # Bizarre edge case because Python's bool is a subclass of int, and therefore
        # True == 1, False == 0, and 10 + True == 11. ¯\_(ツ)_/¯
        self.assertEqual(site.vars.get_value("testvar", default=0, asa=bool), False)
        self.assertEqual(site.vars.get_value("testvar", default=1, asa=bool), True)
        self.assertEqual(site.vars.get_value("testvar", default=False, asa=int), 0)
        self.assertEqual(site.vars.get_value("testvar", default=True, asa=int), 1)

        var = SiteVar.objects.create(site_id=1, name="testvar", value="true")
        self.assertEqual(site.vars.get_value("testvar", asa=bool), True)

        var.value = "False"
        var.save()
        self.assertEqual(site.vars.get_value("testvar", asa=bool), False)

        var.value = ""
        var.save()
        self.assertEqual(site.vars.get_value("testvar", asa=bool), False)

        var.value = "0"
        var.save()
        self.assertEqual(site.vars.get_value("testvar", asa=bool), False)

        var.value = "1"
        var.save()
        self.assertEqual(site.vars.get_value("testvar", asa=bool), True)

        # If default is passed as a string, should still return bool
        var.delete()
        self.assertEqual(site.vars.get_value("testvar", default="True", asa=bool), True)
        self.assertEqual(
            site.vars.get_value("testvar", default="False", asa=bool), False
        )

    def test_get_value_asa_json(self):
        """Test that get_value works with the asa argument for JSON values."""
        site = config.Site.objects.get(pk=1)
        # Because defaults are converted, missing JSON values will raise an error
        with self.assertRaises(json.JSONDecodeError):
            site.vars.get_value("testvar", asa=json.loads)
        self.assertEqual(
            site.vars.get_value("testvar", default=r'{"key": "val"}', asa=json.loads),
            {"key": "val"},
        )
        self.assertEqual(
            site.vars.get_value("testvar", default={"key": "val"}, asa=json.loads),
            {"key": "val"},
        )
        self.assertEqual(
            site.vars.get_value(
                "testvar", default=r'["item1", "item2"]', asa=json.loads
            ),
            ["item1", "item2"],
        )
        self.assertEqual(
            site.vars.get_value("testvar", default=["item1", "item2"], asa=json.loads),
            ["item1", "item2"],
        )

        # Done with defaults, test with stored values
        var = SiteVar.objects.create(
            site_id=1, name="testvar", value=r'{"key": "value"}'
        )
        self.assertEqual(
            site.vars.get_value("testvar", asa=json.loads), {"key": "value"}
        )
        self.assertEqual(site.vars.get_value("testvar"), '{"key": "value"}')
        # If the type of the value does not match the type of the default,
        # raise TypeError
        with self.assertRaises(TypeError):
            site.vars.get_value("testvar", default=[])

        # Should also work with JSON arrays
        var.value = '["value1", "value2"]'
        var.save()
        self.assertEqual(
            site.vars.get_value("testvar", asa=json.loads), ["value1", "value2"]
        )
        self.assertEqual(site.vars.get_value("testvar"), '["value1", "value2"]')


class GetMultipleValuesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site_id = 1
        SiteVar.objects.create(site_id=cls.site_id, name="var1", value="value1")
        SiteVar.objects.create(site_id=cls.site_id, name="var2", value="value2")
        SiteVar.objects.create(site_id=cls.site_id, name="var3", value="value3")

    def test_get_all_values(self):
        """Test that all SiteVars are returned when no names are provided."""
        result = SiteVar.objects.filter(site_id=self.site_id).get_multiple_values()
        expected = {"var1": "value1", "var2": "value2", "var3": "value3"}
        self.assertEqual(result, expected)

    def test_get_specific_values(self):
        """Test that only specified SiteVars are returned."""
        result = SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
            ["var1", "var3"]
        )
        expected = {"var1": "value1", "var3": "value3"}
        self.assertEqual(result, expected)

    def test_get_values_with_defaults(self):
        """Test that missing SiteVars are filled with default values."""
        result = SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
            ["var1", "var4"],
            defaults={"var4": "default_value4"},
        )
        expected = {"var1": "value1", "var4": "default_value4"}
        self.assertEqual(result, expected)

    def test_get_values_with_callable_asa(self):
        """Test that values are transformed using a callable asa."""
        result = SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
            ["var1", "var2"],
            asa=str.upper,
        )
        expected = {"var1": "VALUE1", "var2": "VALUE2"}
        self.assertEqual(result, expected)

    def test_get_values_with_mapping_asa(self):
        """Test that values are transformed using a mapping asa."""
        result = SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
            ["var1", "var2", "var3"],
            asa={"var1": str.upper, "var2": lambda x: x[::-1]},
        )
        expected = {"var1": "VALUE1", "var2": "2eulav", "var3": "value3"}
        self.assertEqual(result, expected)

    def test_get_values_with_defaults_and_asa_callable(self):
        """Test that missing SiteVars are filled with default values and transformed."""
        result = SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
            ["var1", "var4"],
            defaults={"var4": "default_value4"},
            asa=str.upper,
        )
        expected = {"var1": "VALUE1", "var4": "DEFAULT_VALUE4"}
        self.assertEqual(result, expected)

    def test_get_values_with_defaults_and_asa_mapping(self):
        """Test that missing SiteVars are filled with default values and transformed."""
        result = SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
            ["var1", "var4"],
            defaults={"var4": "default_value4"},
            asa={"var1": str.upper, "var4": lambda x: x[::-1]},
        )
        expected = {"var1": "VALUE1", "var4": "4eulav_tluafed"}
        self.assertEqual(result, expected)

    def test_invalid_defaults_argument(self):
        """Test that a TypeError is raised for invalid defaults argument."""
        with self.assertRaises(TypeError):
            SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
                ["var1"], defaults="not_a_mapping"
            )

    def test_invalid_asa_argument(self):
        """Test that a TypeError is raised for invalid asa argument."""
        with self.assertRaises(TypeError):
            SiteVar.objects.filter(site_id=self.site_id).get_multiple_values(
                ["var1"], asa="not_callable_or_mapping"
            )


class SiteVarTemplateTagTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.site = config.Site.objects.get(pk=1)
        cls.sitevar = SiteVar.objects.create(
            site=cls.site, name="testvar", value="testvalue"
        )
        cls.request = RequestFactory().get("/")
        cls.request.site = cls.site

    def test_sitevar_exists(self):
        """Test that the sitevar is retrieved correctly."""
        template = Template("{% load sitevars %}{% sitevar 'testvar' %}")
        rendered = template.render(Context({"request": self.request}))
        self.assertEqual(rendered.strip(), "testvalue")

    def test_sitevar_not_found(self):
        """Test that the default value is returned when sitevar is not found."""
        template = Template(
            "{% load sitevars %}{% sitevar 'nonexistent' 'defaultvalue' %}"
        )
        rendered = template.render(Context({"request": self.request}))
        self.assertEqual(rendered.strip(), "defaultvalue")

    def test_sitevar_with_context(self):
        """Test that the sitevar is retrieved correctly with context."""
        template = Template(
            "{% load sitevars %}{% sitevar 'testvar' as var %}{{ var }}"
        )
        rendered = template.render(Context({"request": self.request}))
        self.assertEqual(rendered.strip(), "testvalue")

    def test_sitevar_with_context_and_default(self):
        """Test that the sitevar is retrieved correctly with context and default value."""
        template = Template(
            "{% load sitevars %}{% sitevar 'nonexistent' default='defaultvalue' as var %}{{ var }}"
        )
        rendered = template.render(Context({"request": self.request}))
        self.assertEqual(rendered.strip(), "defaultvalue")

    def test_sitevar_no_site_middleware(self):
        """Test that the sitevar is retrieved correctly without site middleware."""
        template = Template("{% load sitevars %}{% sitevar 'testvar' %}")
        request = RequestFactory().get("/")
        assert not hasattr(request, "site")

        rendered = template.render(Context({"request": request}))
        self.assertEqual(rendered.strip(), "testvalue")

    @skipIf(
        config.site_model.lower() != "sitevars.placeholdersite",
        "Test only applies to PlaceholderSite model.",
    )
    def test_sitevar_placeholder_without_request_context(self):
        """Test that the sitevar is retrieved correctly without a request in context."""
        template = Template("{% load sitevars %}{% sitevar 'testvar' %}")
        rendered = template.render(Context({}))
        self.assertEqual(rendered.strip(), "testvalue")


class CheckContribSitesComesBeforeSitevarsTest(TestCase):
    @override_settings(
        INSTALLED_APPS=[
            "sitevars",
            "django.contrib.sites",
        ]
    )
    def test_sitevars_before_sites(self):
        result = checks.check_contrib_sites_comes_before_sitevars(None)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Warning)
        self.assertEqual(result[0].id, "sitevars.W001")

    @override_settings(
        INSTALLED_APPS=[
            "django.contrib.sites",
            "sitevars",
        ]
    )
    def test_sites_before_sitevars(self):
        result = checks.check_contrib_sites_comes_before_sitevars(None)
        self.assertEqual(result, [])

    @override_settings(
        INSTALLED_APPS=[
            "django.contrib.sites",
        ]
    )
    def test_sites_only(self):
        # If we're not installed this should never run, but if it does, it should
        # produce no warnings.
        result = checks.check_contrib_sites_comes_before_sitevars(None)
        self.assertEqual(result, [])


class CheckRequestContextProcessorIsInstalledTest(TestCase):
    @override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                    ],
                },
            },
        ]
    )
    def test_context_processor_installed(self):
        """Test that no warning is returned when the context processor is installed."""
        result = checks.check_request_context_processor_is_installed(None)
        self.assertEqual(result, [])

    @override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {
                    "context_processors": [],
                },
            },
        ]
    )
    def test_context_processor_not_installed(self):
        """Test that a warning is returned when the context processor is not installed."""
        result = checks.check_request_context_processor_is_installed(None)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Warning)
        self.assertEqual(result[0].id, "sitevars.W002")
