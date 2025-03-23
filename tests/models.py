import logging
from django.db import models

logger = logging.getLogger("sitevars.testing")


class FakeSiteManager(models.Manager):
    def get_current(self, request):
        # Emulate the behavior of the Django sites framework
        logger.info("FakeSiteManager.get_current() called")
        return self.get(id=1)


class FakeSite(models.Model):
    name = models.CharField(max_length=100, blank=True)
    domain = models.CharField(max_length=100, blank=True)

    objects = FakeSiteManager()

    def __str__(self):
        return self.name

    @classmethod
    def get_current(cls, request):
        """For testing the CURRENT_SITE_METHOD setting."""
        logger.info("FakeSite.get_current() called")
        return cls.objects.get_current(request)


def get_current_site(request):
    """For testing the CURRENT_SITE_FUNCTION setting."""
    logger.info("get_current_site() called")
    return FakeSite.objects.get_current(request)
