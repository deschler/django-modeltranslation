# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy

from modeltranslation.translator import translator, TranslationOptions
from modeltranslation.tests.models import (
    TestModel, FallbackModel, FallbackModel2, FileFieldsModel, OtherFieldsModel, DescriptorModel,
    AbstractModelA, AbstractModelB, Slugged, MetaData, Displayable, Page, RichText, RichTextPage,
    MultitableModelA, MultitableModelB, MultitableModelC, ManagerTestModel, CustomManagerTestModel,
    CustomManager2TestModel, GroupFieldsetsModel, NameModel)


class TestTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
translator.register(TestModel, TestTranslationOptions)


########## Fallback values testing

class FallbackModelTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = "fallback"
translator.register(FallbackModel, FallbackModelTranslationOptions)


class FallbackModel2TranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = {'text': ugettext_lazy('Sorry, translation is not available.')}
translator.register(FallbackModel2, FallbackModel2TranslationOptions)


########## File fields testing

class FileFieldsModelTranslationOptions(TranslationOptions):
    fields = ('title', 'file', 'image',)
translator.register(FileFieldsModel, FileFieldsModelTranslationOptions)


########## Custom fields testing

class OtherFieldsModelTranslationOptions(TranslationOptions):
#    fields = ('int', 'boolean', 'nullboolean', 'csi', 'float', 'decimal',
#              'ip', 'genericip')
    fields = ('int', 'boolean', 'nullboolean', 'csi', 'float', 'decimal',
              'ip', 'date', 'datetime', 'time',)
translator.register(OtherFieldsModel, OtherFieldsModelTranslationOptions)


class DescriptorModelTranslationOptions(TranslationOptions):
    fields = ('trans',)
translator.register(DescriptorModel, DescriptorModelTranslationOptions)


########## Multitable inheritance testing

class MultitableModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)
translator.register(MultitableModelA, MultitableModelATranslationOptions)


class MultitableModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)
translator.register(MultitableModelB, MultitableModelBTranslationOptions)


class MultitableModelCTranslationOptions(TranslationOptions):
    fields = ('titlec',)
translator.register(MultitableModelC, MultitableModelCTranslationOptions)


########## Abstract inheritance testing

class AbstractModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)
translator.register(AbstractModelA, AbstractModelATranslationOptions)


class AbstractModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)
translator.register(AbstractModelB, AbstractModelBTranslationOptions)


########## Fields inheritance testing

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


########## Manager testing

class ManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title', 'visits')
translator.register(ManagerTestModel, ManagerTestModelTranslationOptions)


class CustomManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title',)
translator.register([CustomManagerTestModel, CustomManager2TestModel],
                    CustomManagerTestModelTranslationOptions)


########## TranslationOptions field inheritance testing

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


########## Admin testing

class GroupFieldsetsTranslationOptions(TranslationOptions):
    fields = ('title', 'text',)
translator.register(GroupFieldsetsModel, GroupFieldsetsTranslationOptions)


class NameTranslationOptions(TranslationOptions):
    fields = ('firstname', 'lastname',)
translator.register(NameModel, NameTranslationOptions)
