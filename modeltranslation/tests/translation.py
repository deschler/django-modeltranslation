# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy

from modeltranslation.translator import translator, TranslationOptions
from modeltranslation.tests.models import (
    TestModel, FallbackModel, FallbackModel2,
    FileFieldsModel, OtherFieldsModel, AbstractModelA, AbstractModelB,
    MultitableModelA, MultitableBModelA, MultitableModelC)


class TestTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
translator.register(TestModel, TestTranslationOptions)


class FallbackModelTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = ""
translator.register(FallbackModel, FallbackModelTranslationOptions)


class FallbackModel2TranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = {'text': ugettext_lazy('Sorry, translation is not '
                                             'available.')}
translator.register(FallbackModel2, FallbackModel2TranslationOptions)


class FileFieldsModelTranslationOptions(TranslationOptions):
    fields = ('title', 'file', 'image')
translator.register(FileFieldsModel, FileFieldsModelTranslationOptions)


class OtherFieldsModelTranslationOptions(TranslationOptions):
    fields = ('int',)
translator.register(OtherFieldsModel, OtherFieldsModelTranslationOptions)


class MultitableModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)
translator.register(MultitableModelA, MultitableModelATranslationOptions)


class MultitableModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)
translator.register(MultitableBModelA, MultitableModelBTranslationOptions)


class MultitableModelCTranslationOptions(TranslationOptions):
    fields = ('titlec',)
translator.register(MultitableModelC, MultitableModelCTranslationOptions)


class AbstractModelATranslationOptions(TranslationOptions):
    fields = ('titlea',)
translator.register(AbstractModelA, AbstractModelATranslationOptions)


class AbstractModelBTranslationOptions(TranslationOptions):
    fields = ('titleb',)
translator.register(AbstractModelB, AbstractModelBTranslationOptions)
