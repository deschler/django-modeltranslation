# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy

from modeltranslation.translator import translator, TranslationOptions
from modeltranslation.tests.models import (
    TestModel, FallbackModel, FallbackModel2,
    FileFieldsModel, OtherFieldsModel, AbstractModelA, AbstractModelB,
    MultitableModelA, MultitableBModelA, MultitableModelC,
    ManagerTestModel, CustomManagerTestModel)


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
    fallback_values = {'text': ugettext_lazy('Sorry, translation is not '
                                             'available.')}
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


########## Multitable inheritance testing

class MultitableModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)
translator.register(MultitableModelA, MultitableModelATranslationOptions)


class MultitableModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)
translator.register(MultitableBModelA, MultitableModelBTranslationOptions)


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


########## Manager testing

class ManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title', 'visits')
translator.register(ManagerTestModel, ManagerTestModelTranslationOptions)


class CustomManagerTestModelTranslationOptions(TranslationOptions):
    fields = ('title',)
translator.register(CustomManagerTestModel, CustomManagerTestModelTranslationOptions)


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
