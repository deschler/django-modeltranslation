from pathlib import Path

try:
    from django import VERSION as _django_version

    if _django_version < (3, 2):
        default_app_config = 'modeltranslation.apps.ModeltranslationConfig'
except ImportError:
    pass

__version__ = (Path(__file__).parent / "VERSION").open().read().strip()
