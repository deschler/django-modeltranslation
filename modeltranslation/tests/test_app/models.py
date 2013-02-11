from django.db import models


class News(models.Model):
    title = models.CharField(max_length=50)
    visits = models.SmallIntegerField(blank=True, null=True)


class Other(models.Model):
    name = models.CharField(max_length=50)
