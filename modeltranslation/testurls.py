
from django.conf.urls.defaults import *
from django.contrib import admin
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',

    url(r'^set_language/$',
        'django.views.i18n.set_language',
        {},
        name='set_language'),
    
)