
from django.db import models

from modeltranslation.translator import translator

# Every model registered with the modeltranslation.translator.translator
# is patched to contain additional localized versions for every 
# field specified in the model's translation options.

# Import the project's global "translation.py" which registers model 
# classes and their translation options with the translator object. 
# And because it must import the model classes for the registration
# process, the models.py modules of these apps are fully imported
try: 
    translation_mod = __import__('translation', {}, {}, [''])
except ImportError, exc:
    print "No translation.py found in the project directory."

# After importing all translation modules, all translation classes are 
# registered with the translator. 
translated_app_names = ', '.join(t.__name__ for t in translator._registry.keys())
print "modeltranslation: registered %d applications for translation (%s)." % (len(translator._registry),
                                                                              translated_app_names)
