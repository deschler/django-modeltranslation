from django.db import models


class CurrentSiteManager(models.Manager):
    pass


class Category(models.Model):
    slug = models.SlugField() # registered for translation (using i18n url patterns)

    objects = CurrentSiteManager()
    admin_objects = models.Manager()

    def __unicode__(self):
        return u'%s / %s' % (self.slug_en, self.slug_de)
