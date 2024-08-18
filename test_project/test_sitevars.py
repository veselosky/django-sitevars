from unittest.mock import Mock, patch

from django.apps import apps
from django.contrib.admin import site
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.checks import Warning
from django.db.utils import IntegrityError
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.urls import reverse

from sitevars import checks
from sitevars.context_processors import inject_sitevars
from sitevars.models import SiteVar


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
            if not site.is_registered(model):
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


class ContextProcessorTest(TestCase):
    def test_context_processor_returns_dict(self):
        """Test the context processor."""
        # Create a sitevar
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")

        # Test the context processor returns the sitevar and populates the cache
        with patch("sitevars.context_processors.cache") as mock_cache:
            request = Mock()
            request.site.id = 1
            mock_cache.get.return_value = None
            with self.assertNumQueries(1):
                context = inject_sitevars(request)
            self.assertEqual(context, {"testvar": "testvalue"})
            mock_cache.get.assert_called_once_with("sitevars:1", None)
            mock_cache.set.assert_called_once_with(
                "sitevars:1", {"testvar": "testvalue"}
            )

    def test_cache_used(self):
        """Test that the context processor uses the cache."""
        # Create a sitevar
        SiteVar.objects.create(site_id=1, name="testvar", value="testvalue")

        with patch("sitevars.context_processors.cache") as mock_cache:
            request = Mock()
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
            request = Mock()
            request.site.id = 1
            context = inject_sitevars(request)
            self.assertEqual(context, {"testvar": "testvalue"})
            mock_cache.get.assert_not_called()
            mock_cache.set.assert_not_called()
        self.assertEqual(context, {"testvar": "testvalue"})


class SiteVarModelTest(TestCase):
    def test_sitevar_str(self):
        """Test the string representation of a sitevar."""
        site = Site.objects.get(pk=1)
        sitevar = SiteVar.objects.create(site=site, name="testvar", value="testvalue")
        self.assertEqual(str(sitevar), "testvar=testvalue (example.com)")

    def test_sitevar_unique_together(self):
        """Test that sitevar names are unique per site."""
        site = Site.objects.get(pk=1)
        SiteVar.objects.create(site=site, name="testvar", value="testvalue")
        with self.assertRaises(IntegrityError):
            SiteVar.objects.create(site=site, name="testvar", value="othervalue")

    def test_sitevar_unique_together_different_sites(self):
        """Test that sitevar names are not unique across different sites."""
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

    @override_settings(SITEVARS_USE_CACHE=False)
    def test_sitevar_get_value_no_cache(self):
        """Test that get_value works without cache."""
        site = Site.objects.get(pk=1)
        with patch("sitevars.models.cache") as mock_cache:
            mock_cache.get.return_value = None
            SiteVar.objects.create(site=site, name="testvar", value="testvalue")
            self.assertEqual(site.vars.get_value("testvar"), "testvalue")
            mock_cache.get.assert_not_called()
            mock_cache.set.assert_not_called()
            with self.assertNumQueries(1):
                self.assertEqual(
                    site.vars.get_value("nonexistent", None, asa=int),
                    None,
                )

    def test_get_value_requires_queryset_filtered_by_site(self):
        """Test that get_value raises an error when the queryset is not filtered by site."""
        with self.assertRaises(ValueError):
            SiteVar.objects.get_value("testvar")

    def test_sitevar_get_value_cache_hit(self):
        """Test that get_value works with cache."""
        site = Site.objects.get(pk=1)
        with patch("sitevars.models.cache") as mock_cache:
            mock_cache.get.return_value = {"testvar": "testvalue"}
            self.assertEqual(site.vars.get_value("testvar"), "testvalue")
            mock_cache.get.assert_called_once_with("sitevars:1", None)
            mock_cache.set.assert_not_called()

    def test_sitevar_clear_cache(self):
        """Test that the cache is cleared correctly."""
        site = Site.objects.get(pk=1)
        SiteVar.objects.create(site=site, name="testvar", value="testvalue")
        with patch("sitevars.models.cache") as mock_cache:
            SiteVar.objects.clear_cache(site_id=1)
            mock_cache.delete.assert_called_once_with("sitevars:1")

    def test_sitevar_clear_cache_all_sites(self):
        """Test that the cache is cleared for all sites."""
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
        site = Site.objects.get(pk=1)
        sitevar = SiteVar.objects.create(site=site, name="testvar", value="testvalue")
        with patch("sitevars.models.transaction") as mock_xact:
            sitevar.delete()
            mock_xact.on_commit.assert_called()

    def test_save_clears_cache(self):
        """Test that the cache is cleared on commit when a sitevar is saved."""
        site = Site.objects.get(pk=1)
        sitevar = SiteVar.objects.create(site=site, name="testvar", value="testvalue")
        with patch("sitevars.models.transaction") as mock_xact:
            sitevar.save()
            mock_xact.on_commit.assert_called()


class SiteVarTemplateTagTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.site = Site.objects.get(pk=1)
        cls.sitevar = SiteVar.objects.create(
            site=cls.site, name="testvar", value="testvalue"
        )
        cls.request = Mock()
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
