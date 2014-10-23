# -*- coding: utf-8 -*-
from optparse import make_option

from django.db.models import F, Q
from django.core.management.base import NoArgsCommand

from modeltranslation.translator import translator
from modeltranslation.utils import build_localized_fieldname


class Command(NoArgsCommand):
    help = ('Updates empty values of default translation fields using'
            ' values from original fields (in all translated models).')

    option_list = NoArgsCommand.option_list + (
        make_option('--app', default=None,
                    help='Limit updating values to a single app.'),
    )

    def handle_noargs(self, **options):
        self.verbosity = int(options['verbosity'])
        self.app = options.get('app') or options.get('app_config')

        models = translator.get_registered_models(abstract=False, app=self.app)
        for model in models:
            if self.verbosity > 0:
                self.stdout.write("Updating data of model '%s'\n" % model)
            opts = translator.get_options_for_model(model)
            for field_name in opts.fields.keys():
                def_lang_fieldname = build_localized_fieldname(field_name, opts.default_language)

                # We'll only update fields which do not have an existing value
                q = Q(**{def_lang_fieldname: None})
                field = model._meta.get_field(field_name)
                if field.empty_strings_allowed:
                    q |= Q(**{def_lang_fieldname: ""})

                model._default_manager.filter(q).rewrite(False).update(
                    **{def_lang_fieldname: F(field_name)})
