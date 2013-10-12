from optparse import make_option, OptionValueError

from django import VERSION
from django.core.management.commands.loaddata import Command as LoadDataCommand

# Because this command is used (instead of default loaddata), then settings have been imported
# and we can safely import MT modules
from modeltranslation import settings as mt_settings
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
    leave_locale_alone = mt_settings.LOADDATA_RETAIN_LOCALE  # Django 1.6

    option_list = LoadDataCommand.option_list + (
        make_option('--populate', action='callback', callback=check_mode, dest='populate',
                    type='string',
                    metavar='MODE', help='Using this option will cause fixtures to be loaded under '
                    'auto-population MODE. Allowed values are: %s' % ALLOWED_FOR_PRINT),
    )

    def __init__(self):
        super(Command, self).__init__()
        if mt_settings.LOADDATA_RETAIN_LOCALE and VERSION < (1, 6):
            from django.utils import translation
            self.locale = translation.get_language()

    def handle(self, *fixture_labels, **options):
        if self.can_import_settings and hasattr(self, 'locale'):
            from django.utils import translation
            translation.activate(self.locale)

        mode = options.get('populate')
        if mode is not None:
            with auto_populate(mode):
                return super(Command, self).handle(*fixture_labels, **options)
        else:
            return super(Command, self).handle(*fixture_labels, **options)
