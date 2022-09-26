from rest_framework.serializers import ModelSerializer, ValidationError
from django.conf import settings

from modeltranslation.translator import translator


class ModelTranslitionSerializer(ModelSerializer):
    def to_representation(self, instance):
        result = super().to_representation(instance)
        lang = self.context.get("request").GET.get("lang") or settings.DEFAULT_LANGUAGE
        if lang not in (l[0] for l in settings.LANGUAGES):
            raise ValidationError("This lang is not available")
        if lang is not None:
            registered_models = translator.get_registered_models()
            for model in registered_models:
                if self.__class__.Meta.model == model:
                    fields = translator.get_options_for_model(model).get_field_names()
                    for field in fields:
                        result[field] = getattr(instance, f"{field}_{lang}")
        return result

