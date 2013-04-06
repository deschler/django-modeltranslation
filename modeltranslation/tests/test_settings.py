"""
Get test settings in dict format (for use with settings_override).
"""
from . import settings as _settings

TEST_SETTINGS = dict((k, getattr(_settings, k)) for k in dir(_settings) if k == k.upper())
