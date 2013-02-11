from django.db import models
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager


class Category(models.Model):
    slug = models.SlugField() # registered for translation (using i18n url patterns)
    site = models.ForeignKey(Site)

    objects = CurrentSiteManager()
    admin_objects = models.Manager()

    def __unicode__(self):
        return u'%s / %s' % (self.slug_en, self.slug_de)
