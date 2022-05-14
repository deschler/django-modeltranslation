from pathlib import Path
from django import VERSION as _django_version

__version__ = (Path(__file__).parent / "VERSION").open().read().strip()

if _django_version < (3, 2):
    default_app_config = 'modeltranslation.apps.ModeltranslationConfig'
