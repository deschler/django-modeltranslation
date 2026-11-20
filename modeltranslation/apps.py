from django.apps import AppConfig


class ModeltranslationConfig(AppConfig):
    name = "modeltranslation"
    verbose_name = "Modeltranslation"

    def ready(self) -> None:
        from modeltranslation.models import handle_translation_registrations
        from modeltranslation.translator import patch_collector_related_objects

        patch_collector_related_objects()
        handle_translation_registrations()
