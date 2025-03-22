import logging
from django.apps import AppConfig
from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, router
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


def create_fake_site(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    """
    Create the default FakeSite object.
    """
    try:
        Site = apps.get_model("tests", "FakeSite")
    except LookupError:
        return

    if not router.allow_migrate_model(using, Site):
        return

    if not Site.objects.using(using).exists():
        Site(pk=1, domain="example.com", name="example.com").save(using=using)


class FakeSiteConfig(AppConfig):
    name = "tests"
    verbose_name = "Fake Site"

    def ready(self):
        post_migrate.connect(create_fake_site, sender=self)
