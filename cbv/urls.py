from django.conf.urls import patterns, include, url
from django.conf.urls.i18n import i18n_patterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from app.models import Category
from django.views.generic import DetailView

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cbv.views.home', name='home'),
    url(r'^admin/', include(admin.site.urls)),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
)

urlpatterns += i18n_patterns('',
    url(r'^(?P<slug>.+)/$', DetailView.as_view(model=Category)),
)
