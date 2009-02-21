
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, NoArgsCommand

from modeltranslation.translator import translator
from modeltranslation.utils import build_localized_fieldname

class Command(NoArgsCommand):
    help = 'Updates the default translation fields of all or the specified'\
           'translated application using the value of the original field.'
    # args = '[app_name]'
        
    def handle(self, **options):        
        default_lang = settings.LANGUAGES[0][0]        
        print "Using default language:", default_lang        
        
        for model, trans_opts in translator._registry.items():            
            print "Updating data of model '%s'" % model   
            for obj in model.objects.all():                            
                for fieldname in trans_opts.fields:
                    def_lang_fieldname = build_localized_fieldname(fieldname, default_lang)
                    # print "setting %s from %s to %s." % (def_lang_fieldname, fieldname, obj.__dict__[fieldname])
                    if not getattr(obj, def_lang_fieldname):
                        setattr(obj, def_lang_fieldname, obj.__dict__[fieldname])
                obj.save()
