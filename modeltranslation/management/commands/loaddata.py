from __future__ import annotations

from typing import Any

from argparse import Action, Namespace

from django.core.management.base import CommandParser
from django.core.management.commands.loaddata import Command as LoadDataCommand

# Because this command is used (instead of default loaddata), then settings have been imported
# and we can safely import MT modules
from modeltranslation import settings as mt_settings
from modeltranslation.utils import auto_populate
from modeltranslation._typing import AutoPopulate

ALLOWED = (None, False, "all", "default", "required")
ALLOWED_FOR_PRINT = ", ".join(str(i) for i in (0,) + ALLOWED[1:])  # For pretty-printing


def check_mode(
    option: Command.CheckAction,
    opt_str: str | None,
    value: str,
    parser: CommandParser,
    namespace: Namespace | None = None,
) -> None:
    if value == "0" or value.lower() == "false":
        value = False  # type: ignore[assignment]
    if value not in ALLOWED:
        raise ValueError("%s option can be only one of: %s" % (opt_str, ALLOWED_FOR_PRINT))
    setattr(namespace or parser.values, option.dest, value)  # type: ignore[attr-defined]


class Command(LoadDataCommand):
    leave_locale_alone = mt_settings.LOADDATA_RETAIN_LOCALE  # Django 1.6

    class CheckAction(Action):
        def __call__(
            self,
            parser: CommandParser,  # type: ignore[override]
            namespace: Namespace,
            value: str,  # type: ignore[override]
            option_string: str | None = None,
        ) -> None:
            check_mode(self, option_string, value, parser, namespace)

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--populate",
            action=self.CheckAction,
            type=str,
            dest="populate",
            metavar="MODE",
            help=(
                "Using this option will cause fixtures to be loaded under auto-population MODE. "
                + "Allowed values are: %s" % ALLOWED_FOR_PRINT
            ),
        )

    def handle(self, *fixture_labels: Any, **options: Any) -> str | None:
        mode: AutoPopulate | None = options.get("populate")
        if mode is not None:
            with auto_populate(mode):
                return super().handle(*fixture_labels, **options)
        else:
            return super().handle(*fixture_labels, **options)
