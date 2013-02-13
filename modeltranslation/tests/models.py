# -*- coding: utf-8 -*-
from django.core import validators
from django.db import models
from django.utils.translation import ugettext_lazy


class TestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


########## Fallback values testing

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


########## File fields testing

class FileFieldsModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    file = models.FileField(upload_to='test', null=True, blank=True)
    image = models.ImageField(upload_to='test', null=True, blank=True)


########## Custom fields testing

class OtherFieldsModel(models.Model):
    """
    This class is supposed to include other newly added fields types, so that
    adding new supported field doesn't end in adding new test model.
    """
    # That's rich! PositiveIntegerField is only validated in forms, not in models.
    int = models.PositiveIntegerField(default=42, validators=[validators.MinValueValidator(0)])
    boolean = models.BooleanField()
    nullboolean = models.NullBooleanField()
    csi = models.CommaSeparatedIntegerField(max_length=255)
    float = models.FloatField(blank=True, null=True)
    decimal = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    ip = models.IPAddressField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    datetime = models.DateTimeField(blank=True, null=True)
    time = models.TimeField(blank=True, null=True)
#    genericip = models.GenericIPAddressField(blank=True, null=True)


class FancyDescriptor(object):
    """
    Stupid demo descriptor, that store int in database and return string of that length on get.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner):
        length = instance.__dict__[self.field.name]
        if length is None:
            return ''
        return 'a' * length

    def __set__(self, obj, value):
        if isinstance(value, (int, long)):
            obj.__dict__[self.field.name] = value
        elif isinstance(value, basestring):
            obj.__dict__[self.field.name] = len(value)
        else:
            obj.__dict__[self.field.name] = 0


class FancyField(models.PositiveIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', '')
        super(FancyField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(FancyField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, FancyDescriptor(self))

    def pre_save(self, model_instance, add):
        value = super(FancyField, self).pre_save(model_instance, add)
        # In this part value should be retrieved using descriptor and be a string
        assert isinstance(value, basestring)
        # We put an int to database
        return len(value)


class DescriptorModel(models.Model):
    normal = FancyField()
    trans = FancyField()


########## Multitable inheritance testing

class MultitableModelA(models.Model):
    titlea = models.CharField(ugettext_lazy('title a'), max_length=255)


class MultitableModelB(MultitableModelA):
    titleb = models.CharField(ugettext_lazy('title b'), max_length=255)


class MultitableModelC(MultitableModelB):
    titlec = models.CharField(ugettext_lazy('title c'), max_length=255)


class MultitableModelD(MultitableModelB):
    titled = models.CharField(ugettext_lazy('title d'), max_length=255)


########## Abstract inheritance testing

class AbstractModelA(models.Model):
    titlea = models.CharField(ugettext_lazy('title a'), max_length=255)

    class Meta:
        abstract = True


class AbstractModelB(AbstractModelA):
    titleb = models.CharField(ugettext_lazy('title b'), max_length=255)


########## Fields inheritance testing

class Slugged(models.Model):
    slug = models.CharField(max_length=255)

    class Meta:
        abstract = True


class MetaData(models.Model):
    keywords = models.CharField(max_length=255)

    class Meta:
        abstract = True


class Displayable(Slugged, MetaData):
    class Meta:
        abstract = True


class BasePage(Displayable):
    class Meta:
        abstract = True


class Page(BasePage):
    title = models.CharField(max_length=255)


class RichText(models.Model):
    content = models.CharField(max_length=255)

    class Meta:
        abstract = True


class RichTextPage(Page, RichText):
    pass


########## Admin testing

class DataModel(models.Model):
    data = models.TextField(blank=True, null=True)


class GroupFieldsetsModel(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class NameModel(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    slug = models.SlugField(max_length=100)


########## Manager testing

class ManagerTestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    visits = models.IntegerField(ugettext_lazy('visits'), default=0)

    class Meta:
        ordering = ('-visits',)


class CustomManager(models.Manager):
    def get_query_set(self):
        return super(CustomManager, self).get_query_set().filter(title__contains='a')

    def foo(self):
        return 'bar'


class CustomManagerTestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    objects = CustomManager()


class CustomQuerySet(models.query.QuerySet):
    pass


class CustomManager2(models.Manager):
    def get_query_set(self):
        return CustomQuerySet(self.model, using=self._db)


class CustomManager2TestModel(models.Model):
    title = models.CharField(ugettext_lazy('title'), max_length=255)
    objects = CustomManager2()
