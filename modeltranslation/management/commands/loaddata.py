from __future__ import with_statement
from optparse import make_option, OptionValueError

from django.core.management.commands.loaddata import Command as LoadDataCommand

from modeltranslation.utils import auto_populate


ALLOWED = (None, False, 'all', 'default', 'required')
ALLOWED_FOR_PRINT = ', '.join(str(i) for i in (0, ) + ALLOWED[1:])  # For pretty-printing


def check_mode(option, opt_str, value, parser):
    if value == '0' or value.lower() == 'false':
        value = False
    if value not in ALLOWED:
        raise OptionValueError("%s option can be only one of: %s" % (opt_str, ALLOWED_FOR_PRINT))
    setattr(parser.values, option.dest, value)


class Command(LoadDataCommand):
    option_list = LoadDataCommand.option_list + (
        make_option('--populate', action='callback', callback=check_mode, dest='populate',
                    type='string',
                    metavar='MODE', help='Using this option will cause fixtures to be loaded under '
                    'auto-population MODE. Allowed values are: %s' % ALLOWED_FOR_PRINT),
    )

    def handle(self, *fixture_labels, **options):
        mode = options.get('populate')
        if mode is not None:
            with auto_populate(mode):
                return super(Command, self).handle(*fixture_labels, **options)
        else:
            return super(Command, self).handle(*fixture_labels, **options)
