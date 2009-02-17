# from django.db.models import signals
# from django.utils.functional import curry

#class TranslationMiddleware(object):
    #def process_request(self, request):
        #if hasattr(request, 'LANGUAGE_CODE'):
            #print "TranslationMiddleware: preferred lang=", request.LANGUAGE_CODE
            #update_lang = curry(self.update_lang, request.LANGUAGE_CODE)
            #signals.pre_save.connect(update_lang, dispatch_uid=request, weak=False)
        #else:
            #print "TranslationMiddleware: no lang"
            #pass
    
    
    #def update_lang(self, lang, sender, instance, **kwargs):
        #registry = registration.FieldRegistry()
        #if sender in registry:
            #for field in registry.get_fields(sender):
                #setattr(instance, field.name, lang)                
    
    #def process_response(self, request, response):
        #print "response:", dir(response)
        #signals.pre_save.disconnect(dispatch_uid=request)
        #return response