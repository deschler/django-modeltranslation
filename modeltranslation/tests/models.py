# -*- coding: utf-8 -*-
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
