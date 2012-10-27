# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy

from modeltranslation.translator import translator, TranslationOptions
from modeltranslation.tests.models import (
    TestModel, TestModelWithFallback, TestModelWithFallback2,
    TestModelWithFileFields, TestModelAbstractA, TestModelAbstractB,
    TestModelMultitableA, TestModelMultitableB, TestModelMultitableC)


class TestTranslationOptions(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
translator.register(TestModel, TestTranslationOptions)


class TestTranslationOptionsWithFallback(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = ""
translator.register(TestModelWithFallback,
                    TestTranslationOptionsWithFallback)


class TestTranslationOptionsWithFallback2(TranslationOptions):
    fields = ('title', 'text', 'url', 'email',)
    fallback_values = {'text': ugettext_lazy('Sorry, translation is not '
                                             'available.')}
translator.register(TestModelWithFallback2,
                    TestTranslationOptionsWithFallback2)


class TestTranslationOptionsModelWithFileFields(TranslationOptions):
    fields = ('title', 'file', 'image')
translator.register(TestModelWithFileFields,
                    TestTranslationOptionsModelWithFileFields)


class TranslationOptionsTestModelMultitableA(TranslationOptions):
    fields = ('titlea',)
translator.register(TestModelMultitableA,
                    TranslationOptionsTestModelMultitableA)


class TranslationOptionsTestModelMultitableB(TranslationOptions):
    fields = ('titleb',)
translator.register(TestModelMultitableB,
                    TranslationOptionsTestModelMultitableB)


class TranslationOptionsTestModelMultitableC(TranslationOptions):
    fields = ('titlec',)
translator.register(TestModelMultitableC,
                    TranslationOptionsTestModelMultitableC)


class TranslationOptionsTestModelAbstractA(TranslationOptions):
    fields = ('titlea',)
translator.register(TestModelAbstractA,
                    TranslationOptionsTestModelAbstractA)


class TranslationOptionsTestModelAbstractB(TranslationOptions):
    fields = ('titleb',)
translator.register(TestModelAbstractB,
                    TranslationOptionsTestModelAbstractB)
