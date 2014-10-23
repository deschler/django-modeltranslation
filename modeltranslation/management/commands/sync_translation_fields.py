# -*- coding: utf-8 -*-
"""
Detect new translatable fields in all models and sync database structure.

You will need to execute this command in two cases:

    1. When you add new languages to settings.LANGUAGES.
    2. When you add new translatable fields to your models.

Credits: Heavily inspired by django-transmeta's sync_transmeta_db command.
"""
from optparse import make_option

import django
from django.core.management.base import NoArgsCommand
from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils.six import moves

from modeltranslation.translator import translator


class Command(NoArgsCommand):
    help = ('Detect new translatable fields or new available languages and'
            ' sync database structure. Does not remove columns of removed'
            ' languages or undeclared fields.')

    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
                    help='Do NOT prompt the user for input of any kind.'),
        make_option('--app', default=None,
                    help='Limit looking for missing columns to a single app.'),
    )

    def handle_noargs(self, **options):
        self.cursor = connection.cursor()
        self.introspection = connection.introspection
        self.interactive = options['interactive']
        self.verbosity = int(options['verbosity'])
        self.app = options.get('app') or options.get('app_config')

        found_missing_columns = False
        models = translator.get_registered_models(abstract=False, app=self.app)
        for model in models:
            db_table = model._meta.db_table
            model_full_name = '%s.%s' % (model._meta.app_label, model._meta.object_name)

            opts = translator.get_options_for_model(model)
            for field_name, local_fields in opts.local_fields.items():
                missing_columns = self.find_missing_columns(local_fields, db_table)
                if not missing_columns:
                    continue
                found_missing_columns = True
                field_full_name = '%s.%s' % (model_full_name, field_name)
                if self.verbosity > 0:
                    self.stdout.write('Missing translation columns for field "%s": %s' % (
                        field_full_name, ', '.join(missing_columns.keys())))

                statements = self.generate_add_column_statements(field_name, missing_columns, model)
                if self.interactive or self.verbosity > 0:
                    self.stdout.write('\nStatements to be executed for "%s":' % field_full_name)
                    for statement in statements:
                        self.stdout.write('   %s' % statement)
                if self.interactive:
                    answer = None
                    prompt = ('\nAre you sure that you want to execute the printed statements:'
                              ' (y/n) [n]: ')
                    while answer not in ('', 'y', 'n', 'yes', 'no'):
                        answer = moves.input(prompt).strip()
                        prompt = 'Please answer yes or no: '
                    execute = (answer == 'y' or answer == 'yes')
                else:
                    execute = True
                if execute:
                    if self.verbosity > 0:
                        self.stdout.write('Executing statements...')
                    for statement in statements:
                        self.cursor.execute(statement)
                    if self.verbosity > 0:
                        self.stdout.write('Done')
                else:
                    if self.verbosity > 0:
                        self.stdout.write('Statements not executed')

        if django.VERSION < (1, 6) and found_missing_columns:
            transaction.commit_unless_managed()

        if self.verbosity > 0 and not found_missing_columns:
            self.stdout.write('No new translatable fields detected')

    def find_missing_columns(self, local_fields, db_table):
        """
        Returns a dictionary of (code, column name) for translation fields
        which do not have a column in the database table.
        """
        missing_columns = {}
        db_table_description = self.introspection.get_table_description(self.cursor, db_table)
        db_table_columns = [t[0] for t in db_table_description]
        for field in local_fields:
            db_column = field.db_column if field.db_column else field.name
            if db_column not in db_table_columns:
                missing_columns[field.language] = db_column
        return missing_columns

    def generate_add_column_statements(self, field_name, missing_columns, model):
        """
        Returns database statements needed to add missing columns for the
        field.
        """
        statements = []
        style = no_style()
        qn = connection.ops.quote_name
        db_table = model._meta.db_table
        db_column_type = model._meta.get_field(field_name).db_type(connection)
        for lang_column in missing_columns.values():
            statement = 'ALTER TABLE %s ADD COLUMN %s %s' % (qn(db_table),
                                                             style.SQL_FIELD(qn(lang_column)),
                                                             style.SQL_COLTYPE(db_column_type))
            if not model._meta.get_field(lang_column).null:
                statement += ' ' + style.SQL_KEYWORD('NOT NULL')
            statements.append(statement + ';')
        return statements
