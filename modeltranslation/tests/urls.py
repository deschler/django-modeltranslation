# -*- coding: utf-8 -*-
from django.conf.urls import include, patterns, url
from django.contrib import admin


urlpatterns = patterns(
    '',
    url(r'^set_language/$', 'django.views.i18n.set_language', {},
        name='set_language'),
    url(r'^admin/', include(admin.site.urls)),)
