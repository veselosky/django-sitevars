from django.db import models


class FakeSiteManager(models.Manager):
    def get_current(self, request):
        # Emulate the behavior of the Django sites framework
        return self.get(id=1)


class FakeSite(models.Model):
    name = models.CharField(max_length=100, blank=True)
    domain = models.CharField(max_length=100, blank=True)

    objects = FakeSiteManager()

    def __str__(self):
        return self.name
