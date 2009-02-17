from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import get_language

class TranslationFieldDescriptor(object):
    """
    A descriptor used for the original translated field.
    """
    def __init__(self, name, initial_val=""):
        """
        The ``name`` is the name of the field (which is not available in the
        descriptor by default - this is Python behaviour).
        """
        self.name = name        
        self.val = initial_val

    def __set__(self, instance, value):                
        # print "Descriptor.__set__%s %s %s.%s: %s" % (id(instance), id(self), type(instance), self.name, value)
        lang = get_language()              
        loc_field_name = build_localized_fieldname(self.name, lang)
        
        # also update the translation field of the current language        
        setattr(instance, loc_field_name, value)
        
        # update the original field via the __dict__ to prevent calling the
        # descriptor
        instance.__dict__[self.name] = value
        

    def __get__(self, instance, owner):
        # print "Descriptor.__get__%s %s %s.%s: %s" % (id(instance), id(self), type(instance), self.name, self.val)
        if not instance:
            raise ValueError(u"Translation field '%s' can only be "\
                                "accessed via an instance not via "\
                                "a class." % self.name)
        
        lang = get_language()                
        loc_field_name = build_localized_fieldname(self.name, lang) 
        if hasattr(instance, loc_field_name):            
            return getattr(instance, loc_field_name) or instance.__dict__[self.name]
        return instance.__dict__[self.name]             
        

#def create_model(name, fields=None, app_label='', module='', options=None, admin_opts=None):
    #"""
    #Create specified model.
    #This is taken from http://code.djangoproject.com/wiki/DynamicModels
    #"""
    #class Meta:
        ## Using type('Meta', ...) gives a dictproxy error during model creation
        #pass

    #if app_label:
        ## app_label must be set using the Meta inner class
        #setattr(Meta, 'app_label', app_label)

    ## Update Meta with any options that were provided
    #if options is not None:
        #for key, value in options.iteritems():
            #setattr(Meta, key, value)

    ## Set up a dictionary to simulate declarations within a class
    #attrs = {'__module__': module, 'Meta': Meta}

    ## Add in any fields that were provided
    #if fields:
        #attrs.update(fields)

    ## Create the class, which automatically triggers ModelBase processing
    #model = type(name, (models.Model,), attrs)

    ## Create an Admin class if admin options were provided
    #if admin_opts is not None:
        #class Admin(admin.ModelAdmin):
            #pass
        #for key, value in admin_opts:
            #setattr(Admin, key, value)
        #admin.site.register(model, Admin)

    #return model
   
   
def copy_field(field):
    """Instantiate a new field, with all of the values from the old one, except the    
    to and to_field in the case of related fields.
    
    This taken from http://www.djangosnippets.org/snippets/442/
    """    
    base_kw = dict([(n, getattr(field,n, '_null')) for n in models.fields.Field.__init__.im_func.func_code.co_varnames])
    if isinstance(field, models.fields.related.RelatedField):
        rel = base_kw.get('rel')
        rel_kw = dict([(n, getattr(rel,n, '_null')) for n in rel.__init__.im_func.func_code.co_varnames])
        if isinstance(field, models.fields.related.ForeignKey):
            base_kw['to_field'] = rel_kw.pop('field_name')
        base_kw.update(rel_kw)
    base_kw.pop('self')    
    return field.__class__(**base_kw)
        

def build_localized_fieldname(field_name, lang):
    return '%s_%s' % (field_name, lang)
