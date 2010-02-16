    
from django.conf import settings
from django.db.models.fields import Field, CharField

from modeltranslation.utils import get_language, build_localized_fieldname

class TranslationField(Field):
    """
    The translation field functions as a proxy to the original field which is
    wrapped. 
    
    For every field defined in the model's ``TranslationOptions`` localized
    versions of that field are added to the model depending on the languages
    given in ``settings.LANGUAGES``.

    If for example there is a model ``News`` with a field ``title`` which is
    registered for translation and the ``settings.LANGUAGES`` contains the
    ``de`` and ``en`` languages, the fields ``title_de`` and ``title_en`` will
    be added to the model class. These fields are realized using this 
    descriptor.
    
    The translation field needs to know which language it contains therefore
    that needs to be specified when the field is created.            
    """
    def __init__(self, translated_field, language, *args, **kwargs):
        # Store the originally wrapped field for later
        self.translated_field = translated_field
        self.language = language
        
        # Update the dict of this field with the content of the original one
        # This might be a bit radical?! Seems to work though...
        self.__dict__.update(translated_field.__dict__)        
        
        # Translation are always optional (for now - maybe add some parameters
        # to the translation options for configuring this)
        self.null = True
        self.blank = True
        
        # Adjust the name of this field to reflect the language
        self.attname = build_localized_fieldname(translated_field.name, language)
        self.name = self.attname
        
        # Copy the verbose name and append a language suffix (will e.g. in the
        # admin). This might be a proxy function so we have to check that here.
        if hasattr(translated_field.verbose_name, '_proxy____unicode_cast'):            
            verbose_name = translated_field.verbose_name._proxy____unicode_cast()
        else:
            verbose_name = translated_field.verbose_name                       
        self.verbose_name = '%s [%s]' % (verbose_name, language)
                
    def pre_save(self, model_instance, add):              
        val = super(TranslationField, self).pre_save(model_instance, add)
        if get_language() == self.language and not add:            
            # Rule is: 3. Assigning a value to a translation field of the default language
            #             also updates the original field
            model_instance.__dict__[self.translated_field.name] = val
            #setattr(model_instance, self.attname, orig_val)
            # Also return the original value
            #return orig_val
        return val
                    
    #def get_attname(self):
        #return self.attname       
                
    def get_internal_type(self):
        return self.translated_field.get_internal_type()
        
    def contribute_to_class(self, cls, name):                      
        
        super(TranslationField, self).contribute_to_class(cls, name)
        
        #setattr(cls, 'get_%s_display' % self.name, curry(cls._get_FIELD_display, field=self))
    
#class CurrentLanguageField(CharField):
    #def __init__(self, **kwargs):
        #super(CurrentLanguageField, self).__init__(null=True, max_length=5, **kwargs)
        
    #def contribute_to_class(self, cls, name):
        #super(CurrentLanguageField, self).contribute_to_class(cls, name)
        #registry = CurrentLanguageFieldRegistry()
        #registry.add_field(cls, self)
        
        
#class CurrentLanguageFieldRegistry(object):
    #_registry = {}
    
    #def add_field(self, model, field):
        #reg = self.__class__._registry.setdefault(model, [])
        #reg.append(field)
        
    #def get_fields(self, model):
        #return self.__class__._registry.get(model, [])
    
    #def __contains__(self, model):
        #return model in self.__class__._registry
    
        
