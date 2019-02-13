# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.translation import ugettext_lazy

from modeltranslation.translator import translator, register, TranslationOptions
from modeltranslation.tests.models import (
    TestModel, FallbackModel, FallbackModel2, FileFieldsModel, ForeignKeyModel, OtherFieldsModel,
    DescriptorModel, AbstractModelA, AbstractModelB, Slugged, MetaData, Displayable, Page,
    RichText, RichTextPage, MultitableModelA, MultitableModelB, MultitableModelC, ManagerTestModel,
    CustomManagerTestModel, CustomManager2TestModel, GroupFieldsetsModel, NameModel,
    ThirdPartyRegisteredModel, ProxyTestModel, UniqueNullableModel, OneToOneFieldModel,
    RequiredModel, DecoratedModel, ModelX, ModelY)


class TestTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    empty_values = ''
translator.register(TestModel, TestTranslationOptions)


class UniqueNullableTranslationOptions(TranslationOptions):
    fields = ('title',)
translator.register(UniqueNullableModel, UniqueNullableTranslationOptions)


# ######### Proxy model testing

class ProxyTestTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
translator.register(ProxyTestModel, ProxyTestTranslationOptions)


# ######### Fallback values testing

class FallbackModelTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email', 'description')
    fallback_values = "fallback"
translator.register(FallbackModel, FallbackModelTranslationOptions)


class FallbackModel2TranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = {'text': ugettext_lazy('Sorry, translation is not available.')}
    fallback_undefined = {'title': 'no title'}
translator.register(FallbackModel2, FallbackModel2TranslationOptions)


# ######### File fields testing

class FileFieldsModelTranslationOptions(TranslationOptions):
    fields = ('title', 'file', 'file2', 'image',)
translator.register(FileFieldsModel, FileFieldsModelTranslationOptions)


# ######### Foreign Key / OneToOneField testing

class ForeignKeyModelTranslationOptions(TranslationOptions):
    fields = ('title', 'test', 'optional', 'hidden', 'non',)
translator.register(ForeignKeyModel, ForeignKeyModelTranslationOptions)


class OneToOneFieldModelTranslationOptions(TranslationOptions):
    fields = ('title', 'test', 'optional', 'non',)
translator.register(OneToOneFieldModel, OneToOneFieldModelTranslationOptions)


# ######### Custom fields testing

class OtherFieldsModelTranslationOptions(TranslationOptions):
    fields = ('int', 'boolean', 'nullboolean', 'csi', 'float', 'decimal',
              'ip', 'genericip', 'date', 'datetime', 'time',)
translator.register(OtherFieldsModel, OtherFieldsModelTranslationOptions)


class DescriptorModelTranslationOptions(TranslationOptions):
    fields = ('trans',)
translator.register(DescriptorModel, DescriptorModelTranslationOptions)


# ######### Multitable inheritance testing

class MultitableModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)
translator.register(MultitableModelA, MultitableModelATranslationOptions)


class MultitableModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)
translator.register(MultitableModelB, MultitableModelBTranslationOptions)


class MultitableModelCTranslationOptions(TranslationOptions):
    fields = ('titlec',)
translator.register(MultitableModelC, MultitableModelCTranslationOptions)


# ######### Abstract inheritance testing

class AbstractModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)
translator.register(AbstractModelA, AbstractModelATranslationOptions)


class AbstractModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)
translator.register(AbstractModelB, AbstractModelBTranslationOptions)


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
translator.register(Slugged, SluggedTranslationOptions)
translator.register(MetaData, MetaDataTranslationOptions)
translator.register(RichText, RichTextTranslationOptions)
translator.register(Displayable)
translator.register(Page, PageTranslationOptions)
translator.register(RichTextPage)


# ######### Manager testing

class ManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title', 'visits', 'description')
translator.register(ManagerTestModel, ManagerTestModelTranslationOptions)


class CustomManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title',)
translator.register([CustomManagerTestModel, CustomManager2TestModel],
                    CustomManagerTestModelTranslationOptions)


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

class ThirdPartyTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(ThirdPartyRegisteredModel, ThirdPartyTranslationOptions)


# ######### Admin testing

class GroupFieldsetsTranslationOptions(TranslationOptions):
    fields = ('title', 'text',)
translator.register(GroupFieldsetsModel, GroupFieldsetsTranslationOptions)


class NameTranslationOptions(TranslationOptions):
    fields = ('firstname', 'lastname', 'slug2')
translator.register(NameModel, NameTranslationOptions)


# ######### Required fields testing

class RequiredTranslationOptions(TranslationOptions):
    fields = ('non_req', 'req', 'req_reg', 'req_en_reg')
    required_languages = {
        'en': ('req_reg', 'req_en_reg',),
        'default': ('req_reg',),  # for all other languages
    }
translator.register(RequiredModel, RequiredTranslationOptions)


# ######### Decorated registration testing

@register(DecoratedModel)
class DecoratedTranslationOptions(TranslationOptions):
    fields = ('title',)


# ######### Complex M2M with abstract classes and custom managers

class ModelXOptions(TranslationOptions):
    fields = ('name',)
translator.register(ModelX, ModelXOptions)


class ModelYOptions(TranslationOptions):
    fields = ('title',)
translator.register(ModelY, ModelYOptions)


# ######### 3-rd party with custom manager

if "django.contrib.auth" in settings.INSTALLED_APPS:
    from django.contrib.auth.models import Group

    @register(Group)
    class GroupTranslationOptions(TranslationOptions):
        fields = ('name',)
