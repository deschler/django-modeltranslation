# -*- coding: utf-8 -*-
import six
from django.conf import settings
from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy

from modeltranslation.manager import MultilingualManager


class TestModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class UniqueNullableModel(models.Model):
    title = models.CharField(null=True, unique=True, max_length=255)


# ######### Proxy model testing

class ProxyTestModel(TestModel):
    class Meta:
        proxy = True

    def get_title(self):
        return self.title


# ######### Fallback values testing

class FallbackModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    description = models.CharField(max_length=255, null=True)


class FallbackModel2(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    text = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


# ######### File fields testing

class FileFieldsModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    file = models.FileField(upload_to='modeltranslation_tests', null=True, blank=True)
    file2 = models.FileField(upload_to='modeltranslation_tests')
    image = models.ImageField(upload_to='modeltranslation_tests', null=True, blank=True)


# ######### Foreign Key / OneToOneField testing

class NonTranslated(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)


class ForeignKeyModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    test = models.ForeignKey(
        TestModel, null=True, related_name="test_fks", on_delete=models.CASCADE,
    )
    optional = models.ForeignKey(TestModel, blank=True, null=True, on_delete=models.CASCADE)
    hidden = models.ForeignKey(
        TestModel, blank=True, null=True, related_name="+", on_delete=models.CASCADE,
    )
    non = models.ForeignKey(
        NonTranslated, blank=True, null=True, related_name="test_fks", on_delete=models.CASCADE,
    )
    untrans = models.ForeignKey(
        TestModel, blank=True, null=True, related_name="test_fks_un", on_delete=models.CASCADE,
    )


class OneToOneFieldModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    test = models.OneToOneField(
        TestModel, null=True, related_name="test_o2o", on_delete=models.CASCADE,
    )
    optional = models.OneToOneField(TestModel, blank=True, null=True, on_delete=models.CASCADE)
    # No hidden option for OneToOne
    non = models.OneToOneField(
        NonTranslated, blank=True, null=True, related_name="test_o2o", on_delete=models.CASCADE,
    )


# ######### Custom fields testing

class OtherFieldsModel(models.Model):
    """
    This class is supposed to include other newly added fields types, so that
    adding new supported field doesn't end in adding new test model.
    """
    # That's rich! PositiveIntegerField is only validated in forms, not in models.
    int = models.PositiveIntegerField(default=42, validators=[validators.MinValueValidator(0)])
    boolean = models.BooleanField(default=False)
    nullboolean = models.NullBooleanField()
    csi = models.CommaSeparatedIntegerField(max_length=255)
    ip = models.IPAddressField(blank=True, null=True)
    float = models.FloatField(blank=True, null=True)
    decimal = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    datetime = models.DateTimeField(blank=True, null=True)
    time = models.TimeField(blank=True, null=True)
    genericip = models.GenericIPAddressField(blank=True, null=True)


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
        if isinstance(value, six.integer_types):
            obj.__dict__[self.field.name] = value
        elif isinstance(value, six.string_types):
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
        assert isinstance(value, six.string_types)
        # We put an int to database
        return len(value)


class DescriptorModel(models.Model):
    normal = FancyField()
    trans = FancyField()


# ######### Multitable inheritance testing

class MultitableModelA(models.Model):
    titlea = models.CharField(gettext_lazy('title a'), max_length=255)


class MultitableModelB(MultitableModelA):
    titleb = models.CharField(gettext_lazy('title b'), max_length=255)


class MultitableModelC(MultitableModelB):
    titlec = models.CharField(gettext_lazy('title c'), max_length=255)


class MultitableModelD(MultitableModelB):
    titled = models.CharField(gettext_lazy('title d'), max_length=255)


# ######### Abstract inheritance testing

class AbstractModelA(models.Model):
    titlea = models.CharField(gettext_lazy('title a'), max_length=255)

    def __init__(self, *args, **kwargs):
        super(AbstractModelA, self).__init__(*args, **kwargs)
        self.titlea = 'title_a'

    class Meta:
        abstract = True


class AbstractModelB(AbstractModelA):
    titleb = models.CharField(gettext_lazy('title b'), max_length=255)

    def __init__(self, *args, **kwargs):
        super(AbstractModelB, self).__init__(*args, **kwargs)
        self.titleb = 'title_b'


# ######### Fields inheritance testing

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


# ######### Admin testing

class DataModel(models.Model):
    data = models.TextField(blank=True, null=True)


class GroupFieldsetsModel(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)


class NameModel(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    age = models.CharField(max_length=50)
    slug = models.SlugField(max_length=100)
    slug2 = models.SlugField(max_length=100)


# ######### Integration testing

class ThirdPartyModel(models.Model):
    name = models.CharField(max_length=20)


class ThirdPartyRegisteredModel(models.Model):
    name = models.CharField(max_length=20)


# ######### Manager testing
class FilteredManager(MultilingualManager):
    def get_queryset(self):
        # always return empty queryset
        return super(FilteredManager, self).get_queryset().filter(pk=None)


class FilteredTestModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    objects = FilteredManager()


class ForeignKeyFilteredModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    test = models.ForeignKey(
        FilteredTestModel, null=True, related_name="test_fks", on_delete=models.CASCADE,
    )


class ManagerTestModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    visits = models.IntegerField(gettext_lazy('visits'), default=0)
    description = models.CharField(max_length=255, null=True)

    class Meta:
        ordering = ('-visits',)


class CustomManager(models.Manager):
    def get_queryset(self):
        sup = super(CustomManager, self)
        queryset = sup.get_queryset() if hasattr(sup, 'get_queryset') else sup.get_query_set()
        return queryset.filter(title__contains='a').exclude(description__contains='x')
    get_query_set = get_queryset

    def custom_qs(self):
        sup = super(CustomManager, self)
        queryset = sup.get_queryset() if hasattr(sup, 'get_queryset') else sup.get_query_set()
        return queryset

    def foo(self):
        return 'bar'


class CustomManagerTestModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    description = models.CharField(max_length=255, null=True, db_column='xyz')
    objects = CustomManager()

    another_mgr_name = CustomManager()


class CustomQuerySet(models.query.QuerySet):
    pass


class CustomManager2(models.Manager):
    def get_queryset(self):
        return CustomQuerySet(self.model, using=self._db)
    get_query_set = get_queryset


class CustomManager2TestModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    objects = CustomManager2()


class CustomManagerAbstract(models.Manager):
    pass


class CustomManagerBaseModel(models.Model):
    needs_translation = models.BooleanField(default=False)

    objects = models.Manager()  # ensures objects is the default manager
    translations = CustomManagerAbstract()

    class Meta:
        abstract = True


class CustomManagerChildTestModel(CustomManagerBaseModel):
    title = models.CharField(gettext_lazy('title'), max_length=255)

    objects = CustomManager2()


class PlainChildTestModel(CustomManagerBaseModel):
    title = models.CharField(gettext_lazy('title'), max_length=255)


# ######### Required fields testing

class RequiredModel(models.Model):
    non_req = models.CharField(max_length=10, blank=True)
    req = models.CharField(max_length=10)
    req_reg = models.CharField(max_length=10)
    req_en_reg = models.CharField(max_length=10)


# ######### Name collision registration testing

class ConflictModel(models.Model):
    title = models.CharField(gettext_lazy('title'), max_length=255)
    title_de = models.IntegerField()


class AbstractConflictModelA(models.Model):
    title_de = models.IntegerField()

    class Meta:
        abstract = True


class AbstractConflictModelB(AbstractConflictModelA):
    title = models.CharField(gettext_lazy('title'), max_length=255)


class MultitableConflictModelA(models.Model):
    title_de = models.IntegerField()


class MultitableConflictModelB(MultitableConflictModelA):
    title = models.CharField(gettext_lazy('title'), max_length=255)


# ######### Complex M2M with abstract classes and custom managers

class CustomQuerySetX(models.query.QuerySet):
    pass


class CustomManagerX(models.Manager):
    def get_queryset(self):
        return CustomQuerySetX(self.model, using=self._db)
    get_query_set = get_queryset


class AbstractBaseModelX(models.Model):
    name = models.CharField(max_length=255)
    objects = CustomManagerX()

    class Meta:
        abstract = True


class AbstractModelX(AbstractBaseModelX):
    class Meta:
        abstract = True


class ModelX(AbstractModelX):
    pass


class AbstractModelXY(models.Model):
    model_x = models.ForeignKey('ModelX', on_delete=models.CASCADE)
    model_y = models.ForeignKey('ModelY', on_delete=models.CASCADE)

    class Meta:
        abstract = True


class ModelXY(AbstractModelXY):
    pass


class CustomManagerY(models.Manager):
    pass


class AbstractModelY(models.Model):
    title = models.CharField(max_length=255)
    xs = models.ManyToManyField('ModelX', through='ModelXY')
    objects = CustomManagerY()

    class Meta:
        abstract = True


class ModelY(AbstractModelY):
    pass

# Non-abstract base models whos Manager is not allowed to be overwritten


if "django.contrib.auth" in settings.INSTALLED_APPS:
    from django.contrib.auth.models import Permission

    class InheritedPermission(Permission):
        translated_var = models.CharField(max_length=255)
