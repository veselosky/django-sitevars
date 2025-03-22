from django.db import models


class FakeSite(models.Model):
    name = models.CharField(max_length=100, blank=True)
    domain = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
