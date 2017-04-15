# -*- coding: utf-8 -*-
from django.db.models import Q
from django.core.management.base import BaseCommand
from django.conf import settings

from optparse import make_option

from modeltranslation.settings import DEFAULT_LANGUAGE
from modeltranslation.translator import translator
from modeltranslation.utils import build_localized_fieldname, translate


class Command(BaseCommand):
    help = ('Translates fields from the default language'
            'to specified.')

    option_list = BaseCommand.option_list + (
        make_option('--to',
            dest='TO_LANG',
            default=False,
            help='Translate to lang'),
        )

    def handle(self, *args, **options):
        TO_LANG = options['TO_LANG']
        LANGUAGES = [i[0] for i in settings.LANGUAGES]
        if TO_LANG and TO_LANG in LANGUAGES:
            print "Using default language:", DEFAULT_LANGUAGE
            for model, trans_opts in translator._registry.items():
                print "Translating data of model '%s'" % model
                for fieldname in trans_opts.fields:
                    def_from_lang_fieldname = build_localized_fieldname(fieldname, DEFAULT_LANGUAGE)
                    def_to_lang_fieldname = build_localized_fieldname(fieldname, TO_LANG)
                    print "  Field from %s to %s" % (def_from_lang_fieldname, def_to_lang_fieldname)
                    instances = model.objects.exclude(
                        Q(**{def_from_lang_fieldname: None}) |
                        Q(**{def_from_lang_fieldname: ""})
                    ).filter(
                        Q(**{def_to_lang_fieldname: None}) |
                        Q(**{def_to_lang_fieldname: ""})
                    )
                    for i in instances:
                        text = i.__dict__[def_from_lang_fieldname]
                        translated = translate(u"%s" % text, DEFAULT_LANGUAGE, TO_LANG)
                        print "    Text %s to %s." % (text, translated,)
                        setattr(i, def_to_lang_fieldname, translated.capitalize())
                        i.save()

