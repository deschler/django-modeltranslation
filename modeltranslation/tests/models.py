# -*- coding: utf-8 -*-
from django.core import validators
from django.db import models
from django.utils.translation import ugettext_lazy


class TestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class FallbackModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class FallbackModel2(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class FileFieldsModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    file = models.FileField(upload_to='test', null=True, blank=True)
    image = models.ImageField(upload_to='test', null=True, blank=True)


class OtherFieldsModel(models.Model):
    """
    This class is supposed to include other newly added fields types, so that
    adding new supported field doesn't end in adding new test model.
    """
    # That's rich! PositiveIntegerField is only validated in forms, not in models.
    int = models.PositiveIntegerField(default=42, validators=[validators.MinValueValidator(0)])
    boolean = models.BooleanField()
    nullboolean = models.NullBooleanField()


class MultitableModelA(models.Model):
    titlea = models.CharField(ugettext_lazy('title a'), max_length=255)


class MultitableBModelA(MultitableModelA):
    titleb = models.CharField(ugettext_lazy('title b'), max_length=255)


class MultitableModelC(MultitableBModelA):
    titlec = models.CharField(ugettext_lazy('title c'), max_length=255)


class MultitableDTestModel(MultitableBModelA):
    titled = models.CharField(ugettext_lazy('title d'), max_length=255)


class AbstractModelA(models.Model):
    titlea = models.CharField(ugettext_lazy('title a'), max_length=255)

    class Meta:
        abstract = True


class AbstractModelB(AbstractModelA):
    titleb = models.CharField(ugettext_lazy('title b'), max_length=255)


class DataModel(models.Model):
    data = models.TextField(blank=True, null=True)


class ManagerTestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    visits = models.IntegerField(ugettext_lazy('visits'), default=0)


class CustomManager(models.Manager):
    def get_query_set(self):
        return super(CustomManager, self).get_query_set().filter(title__contains='a')

    def foo(self):
        return 'bar'


class CustomManagerTestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    objects = CustomManager()
