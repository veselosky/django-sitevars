from unittest import skipIf
from unittest.mock import Mock, patch, ANY

from django.apps import apps
from django.contrib.admin import site as adminsite
from django.contrib.auth.models import User
from django.core.checks import Warning
from django.db import transaction
from django.db.utils import IntegrityError
from django.template import Context, Template
from django.test import TestCase, TransactionTestCase, override_settings, RequestFactory
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
    @override_settings(SITEVARS_USE_CACHE=False)
    def test_use_cache_false(self):
        """Test the use_cache property when SITEVARS_USE_CACHE is False."""
        self.assertFalse(config.use_cache)

    def test_use_cache_default(self):
        """Test the use_cache property."""
        self.assertTrue(config.use_cache)

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

        # Test the context processor returns the sitevar and populates the cache
        with patch("sitevars.context_processors.cache") as mock_cache:
            request = RequestFactory().get("/")
            # Simulate site middleware
            request.site = Mock()
            request.site.id = 1
            mock_cache.get.return_value = None
            with self.assertNumQueries(1):
                context = inject_sitevars(request)
            self.assertEqual(context, {"testvar": "testvalue"})
            mock_cache.get.assert_called_once_with("sitevars:1", None)
            mock_cache.set.assert_called_once_with(
                "sitevars:1", {"testvar": "testvalue"}
            )

    def test_context_processor_returns_dict__without_site_middleware(self):
        """Test the context processor when sites middleware not installed."""
        # Create a sitevar
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")

        # Test the context processor returns the sitevar and populates the cache
        with patch("sitevars.context_processors.cache") as mock_cache:
            request = RequestFactory().get("/")
            assert not hasattr(request, "site")
            mock_cache.get.return_value = None

            context = inject_sitevars(request)

            self.assertEqual(context, {"testvar": "testvalue"})

    def test_cache_used(self):
        """Test that the context processor uses the cache."""
        # Create a sitevar
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")

        with patch("sitevars.context_processors.cache") as mock_cache:
            request = RequestFactory().get("/")
            request.site = Mock()
            request.site.id = 1
            mock_cache.get.return_value = {"testvar": "testvalue"}
            with self.assertNumQueries(0):
                context = inject_sitevars(request)
            self.assertEqual(context, {"testvar": "testvalue"})
            mock_cache.get.assert_called_once_with("sitevars:1", None)
            mock_cache.set.assert_not_called()

    @override_settings(SITEVARS_USE_CACHE=False)
    def test_context_processor_caching_off(self):
        """Test the context processor with caching off."""
        conf = apps.get_app_config("sitevars")
        self.assertFalse(conf.use_cache)  # Because SITEVARS_USE_CACHE=False

        # Create a sitevar
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")

        with patch("sitevars.context_processors.cache") as mock_cache:
            request = RequestFactory().get("/")
            request.site = Mock()
            request.site.id = 1
            context = inject_sitevars(request)
            self.assertEqual(context, {"testvar": "testvalue"})
            mock_cache.get.assert_not_called()
            mock_cache.set.assert_not_called()
        self.assertEqual(context, {"testvar": "testvalue"})


class SiteVarModelTest(TransactionTestCase):
    # Note: we use TransactionTestCase to manually manage transactions where TestCase
    # would rollback the transaction before the cache is cleared.
    def test_sitevar_str(self):
        """Test the string representation of a sitevar."""
        sitevar = SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        self.assertEqual(str(sitevar), "testvar=testvalue (example.com)")

    def test_sitevar_unique_together(self):
        """Test that sitevar names are unique per site."""
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        with self.assertRaises(IntegrityError):
            SiteVar.objects.create(site_id=1, name="testvar", value="othervalue")

    @skipIf(
        config.site_model.lower() == "sitevars.placeholdersite",
        "Test does not apply to when using PlaceholderSite model.",
    )
    def test_sitevar_unique_together_different_sites(self):
        """Test that sitevar names are not unique across different sites."""
        Site = apps.get_model(*config.site_model.split("."))
        site1 = Site.objects.get(pk=1)
        site2 = Site.objects.create(domain="example2.com", name="example2.com")
        SiteVar.objects.create(site=site1, name="testvar", value="testvalue")
        SiteVar.objects.create(site=site2, name="testvar", value="othervalue")
        self.assertEqual(
            SiteVar.objects.filter(site=site2).get_value("testvar"), "othervalue"
        )
        self.assertEqual(
            SiteVar.objects.filter(site=site1).get_value("testvar"), "testvalue"
        )

    @skipIf(
        config.site_model.lower() == "sitevars.placeholdersite",
        "Test does not apply to when using PlaceholderSite model.",
    )
    def test_get_value_requires_queryset_filtered_by_site(self):
        """Test that get_value raises an error when the queryset is not filtered by site."""
        with self.assertRaises(ValueError):
            SiteVar.objects.get_value("testvar")

    @skipIf(
        config.site_model.lower() != "sitevars.placeholdersite",
        "Test only applies to PlaceholderSite model.",
    )
    def test_get_value_placeholder_site(self):
        """Test that get_value automatically filters queries when using the placeholder site."""
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        with self.assertNumQueries(1):
            self.assertEqual(SiteVar.objects.get_value("testvar"), "testvalue")

    @override_settings(SITEVARS_USE_CACHE=False)
    def test_sitevar_get_value_no_cache(self):
        """Test that get_value honors the use_cache app setting."""
        Site = apps.get_model(*config.site_model.split("."))
        site = Site.objects.get(pk=1)
        with patch("sitevars.models.cache") as mock_cache:
            mock_cache.get.return_value = None
            SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
            self.assertEqual(site.vars.get_value("testvar"), "testvalue")
            mock_cache.get.assert_not_called()
            mock_cache.set.assert_not_called()
            with self.assertNumQueries(1):
                self.assertEqual(
                    site.vars.get_value("nonexistent", None, asa=int),
                    None,
                )

    def test_sitevar_get_value_cache_hit(self):
        """Test that get_value uses the cache."""
        Site = apps.get_model(*config.site_model.split("."))
        site = Site.objects.get(pk=1)
        with patch("sitevars.models.cache") as mock_cache:
            mock_cache.get.return_value = {"testvar": "testvalue"}
            with self.assertNumQueries(0):
                self.assertEqual(site.vars.get_value("testvar"), "testvalue")
            mock_cache.get.assert_called_once_with("sitevars:1", None)
            mock_cache.set.assert_not_called()

    def test_get_value_ignores_cache_inside_transaction(self):
        """Test that the cache is ignored inside a transaction.

        Because transactions can rollback (and there is no transaction.on_rollback we
        can use to detect that), there's a potential for the cache to get out of sync
        if we both write (which clears the cache) and then read (which repopulates the
        cache) inside a transaction that is then rolled back. To avoid this, we ignore
        the cache inside a transaction. This is an edge case that is unlikely (though
        not impossible) to occur in production use, but always happens in TestCase
        tests (which is why we use TransactionTestCase).
        """
        Site = apps.get_model(*config.site_model.split("."))
        site = Site.objects.get(pk=1)
        with transaction.atomic():
            # Attempt to retrieve a sitevar. This would normally populate the cache.
            with patch("sitevars.models.cache") as mock_cache:
                val = site.vars.get_value("testvar", None)
                mock_cache.get.assert_not_called()
                mock_cache.set.assert_not_called()
                self.assertIsNone(val)

            # Cache should still be cleared on write
            with patch("sitevars.models.transaction") as mock_xact:
                SiteVar.objects.create(site=site, name="testvar", value="testvalue")
                mock_xact.on_commit.assert_called_once_with(ANY)

            # The cache should not be used here
            with patch("sitevars.models.cache") as mock_cache:
                with self.assertNumQueries(1):
                    self.assertEqual(site.vars.get_value("testvar"), "testvalue")
                mock_cache.get.assert_not_called()
                mock_cache.set.assert_not_called()

    def test_sitevar_clear_cache(self):
        """Test that the cache is cleared correctly."""
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        with patch("sitevars.models.cache") as mock_cache:
            SiteVar.objects.clear_cache(site_id=1)
            mock_cache.delete.assert_called_once_with("sitevars:1")

    def test_sitevar_clear_cache_all_sites(self):
        """Test that the cache is cleared for all sites."""
        Site = apps.get_model(*config.site_model.split("."))
        site1 = Site.objects.get(pk=1)
        site2 = Site.objects.create(domain="example2.com", name="example2.com")
        SiteVar.objects.create(site=site1, name="testvar", value="testvalue")
        SiteVar.objects.create(site=site2, name="testvar", value="othervalue")
        with patch("sitevars.models.cache") as mock_cache:
            SiteVar.objects.clear_cache()
            mock_cache.delete.assert_any_call("sitevars:1")
            mock_cache.delete.assert_any_call("sitevars:2")

    def test_delete_clears_cache(self):
        """Test that the cache is cleared on commit when a sitevar is deleted."""
        sitevar = SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        with patch("sitevars.models.transaction") as mock_xact:
            sitevar.delete()
            mock_xact.on_commit.assert_called()

    def test_save_clears_cache(self):
        """Test that the cache is cleared on commit when a sitevar is saved."""
        sitevar = SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")
        with patch("sitevars.models.transaction") as mock_xact:
            sitevar.save()
            mock_xact.on_commit.assert_called()


class SiteVarTemplateTagTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        Site = apps.get_model(*config.site_model.split("."))
        cls.site = Site.objects.get(pk=1)
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
