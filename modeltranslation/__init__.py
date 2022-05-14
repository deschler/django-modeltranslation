from pathlib import Path

__version__ = (Path(__file__).parent / "VERSION").open().read().strip()

default_app_config = 'modeltranslation.apps.ModeltranslationConfig'
