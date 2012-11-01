# -*- coding: utf-8 -*-
try:
    from django.conf.urls import include, patterns, url
    assert (include, patterns, url)  # Workaround for pyflakes issue #13
except ImportError:  # Django 1.3 fallback
    from django.conf.urls.defaults import include, patterns, url  # NOQA
from django.contrib import admin


urlpatterns = patterns(
    '',
    url(r'^set_language/$', 'django.views.i18n.set_language', {},
        name='set_language'),
    url(r'^admin/', include(admin.site.urls)),)
