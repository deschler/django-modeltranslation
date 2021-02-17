# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.translation import gettext_lazy

from modeltranslation.translator import translator, register, TranslationOptions
from modeltranslation.tests import models


@register(models.TestModel)
class TestTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    empty_values = ''


@register(models.UniqueNullableModel)
class UniqueNullableTranslationOptions(TranslationOptions):
    fields = ('title',)


# ######### Proxy model testing

@register(models.ProxyTestModel)
class ProxyTestTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)


# ######### Fallback values testing

@register(models.FallbackModel)
class FallbackModelTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email', 'description')
    fallback_values = "fallback"


@register(models.FallbackModel2)
class FallbackModel2TranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = {'text': gettext_lazy('Sorry, translation is not available.')}
    fallback_undefined = {'title': 'no title'}


# ######### File fields testing

@register(models.FileFieldsModel)
class FileFieldsModelTranslationOptions(TranslationOptions):
    fields = ('title', 'file', 'file2', 'image',)


# ######### Foreign Key / OneToOneField testing

@register(models.ForeignKeyModel)
class ForeignKeyModelTranslationOptions(TranslationOptions):
    fields = ('title', 'test', 'optional', 'hidden', 'non',)


@register(models.OneToOneFieldModel)
class OneToOneFieldModelTranslationOptions(TranslationOptions):
    fields = ('title', 'test', 'optional', 'non',)


@register(models.FilteredTestModel)
class FilteredTestModelTranslationOptions(TranslationOptions):
    fields = ('title', )


@register(models.ForeignKeyFilteredModel)
class ForeignKeyFilteredModelTranslationOptions(TranslationOptions):
    fields = ('title', )

# ######### Custom fields testing


@register(models.OtherFieldsModel)
class OtherFieldsModelTranslationOptions(TranslationOptions):
    fields = ('int', 'boolean', 'nullboolean', 'csi', 'float', 'decimal',
              'ip', 'genericip', 'date', 'datetime', 'time',)


@register(models.DescriptorModel)
class DescriptorModelTranslationOptions(TranslationOptions):
    fields = ('trans',)


# ######### Multitable inheritance testing

@register(models.MultitableModelA)
class MultitableModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)


@register(models.MultitableModelB)
class MultitableModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)


@register(models.MultitableModelC)
class MultitableModelCTranslationOptions(TranslationOptions):
    fields = ('titlec',)


# ######### Abstract inheritance testing

@register(models.AbstractModelA)
class AbstractModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)


@register(models.AbstractModelB)
class AbstractModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)


# ######### Fields inheritance testing

class SluggedTranslationOptions(TranslationOptions):
    fields = ('slug',)


class MetaDataTranslationOptions(TranslationOptions):
    fields = ('keywords',)


class RichTextTranslationOptions(TranslationOptions):
    fields = ('content',)


class PageTranslationOptions(TranslationOptions):
    fields = ('title',)


# BasePage left unregistered intentionally.
translator.register(models.Slugged, SluggedTranslationOptions)
translator.register(models.MetaData, MetaDataTranslationOptions)
translator.register(models.RichText, RichTextTranslationOptions)
translator.register(models.Displayable)
translator.register(models.Page, PageTranslationOptions)
translator.register(models.RichTextPage)


# ######### Manager testing

@register(models.ManagerTestModel)
class ManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title', 'visits', 'description')


@register([
    models.CustomManagerTestModel,
    models.CustomManager2TestModel,
    models.CustomManagerChildTestModel,
    models.PlainChildTestModel
])
class CustomManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title',)


# ######### TranslationOptions field inheritance testing

class FieldInheritanceATranslationOptions(TranslationOptions):
    fields = ['titlea']


class FieldInheritanceBTranslationOptions(FieldInheritanceATranslationOptions):
    fields = ['titleb']


class FieldInheritanceCTranslationOptions(FieldInheritanceBTranslationOptions):
    fields = ['titlec']


class FieldInheritanceDTranslationOptions(FieldInheritanceBTranslationOptions):
    fields = ('titled',)


class FieldInheritanceETranslationOptions(FieldInheritanceCTranslationOptions,
                                          FieldInheritanceDTranslationOptions):
    fields = ('titlee',)


# ######### Integration testing

@register(models.ThirdPartyRegisteredModel)
class ThirdPartyTranslationOptions(TranslationOptions):
    fields = ('name',)


# ######### Admin testing

@register(models.GroupFieldsetsModel)
class GroupFieldsetsTranslationOptions(TranslationOptions):
    fields = ('title', 'text',)


@register(models.NameModel)
class NameTranslationOptions(TranslationOptions):
    fields = ('firstname', 'lastname', 'slug2')


# ######### Required fields testing

@register(models.RequiredModel)
class RequiredTranslationOptions(TranslationOptions):
    fields = ('non_req', 'req', 'req_reg', 'req_en_reg')
    required_languages = {
        'en': ('req_reg', 'req_en_reg',),
        'default': ('req_reg',),  # for all other languages
    }


# ######### Complex M2M with abstract classes and custom managers

@register(models.ModelX)
class ModelXOptions(TranslationOptions):
    fields = ('name',)


@register(models.ModelY)
class ModelYOptions(TranslationOptions):
    fields = ('title',)


# ######### 3-rd party with custom manager

if "django.contrib.auth" in settings.INSTALLED_APPS:
    from django.contrib.auth.models import Group
    from .models import InheritedPermission

    @register(Group)
    class GroupTranslationOptions(TranslationOptions):
        fields = ('name',)

    @register(InheritedPermission)
    class InheritedPermissionOptions(TranslationOptions):
        fields = ('translated_var',)
        required_languages = [x[0] for x in settings.LANGUAGES]
