from django.contrib.admin import site
from models import Category
from modeltranslation.admin import TranslationAdmin


class CategoryAdmin(TranslationAdmin):
    def queryset(self, request):
        qs = self.model.admin_objects.get_query_set()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

site.register(Category, CategoryAdmin)
