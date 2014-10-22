from django.db import models


class News(models.Model):
    title = models.CharField(max_length=50)
    visits = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        app_label = 'managed_app'


class Other(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = 'managed_app'
