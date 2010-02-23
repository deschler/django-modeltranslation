# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from modeltranslation.translator import translator

# Every model registered with the modeltranslation.translator.translator
# is patched to contain additional localized versions for every 
# field specified in the model's translation options.

# Import the project's global "translation.py" which registers model 
# classes and their translation options with the translator object. 
# This requires an extra settings entry, because I see no other way
# to determine the module name of the project
# TODO: Consider removal of TRANSLATION_REGISTRY
#       It is supposed to be kept in the project's root and this has to be in
#       PYTHONPATH anyway.
try: 
    translation_mod = __import__(settings.TRANSLATION_REGISTRY, {}, {}, [''])
except ImportError, exc:
    raise ImportError("modeltranslation: TRANSLATION_REGISTRY '%s' not found." 
                      % settings.TRANSLATION_REGISTRY)

# After importing all translation modules, all translation classes are 
# registered with the translator.
if settings.DEBUG:
    translated_app_names = ', '.join(t.__name__ for t in translator._registry.keys())
    print "modeltranslation: registered %d applications for translation (%s)." % (len(translator._registry), translated_app_names)
