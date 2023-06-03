from modeltranslation.translator import rewrite_lookup_key


def delete_mt_init(sender, instance, **kwargs):
    """
    Delete _mt_init attribute from instance.
    """
    if hasattr(instance, '_mt_init'):
        del instance._mt_init


def populate_update_fields(sender, instance, signal, raw, update_fields, **kwargs):
    """
    Populate update_fields with translated fields when save is called with
    update_fields argument.
    """
    if update_fields is not None:
        translated_update_fields = []
        for field in update_fields:
            translated_update_fields.append(field)
            translated_update_fields.append(rewrite_lookup_key(instance.__class__, field))
        translated_update_fields = frozenset(translated_update_fields)
        if update_fields != translated_update_fields:
            instance.save(update_fields=translated_update_fields, **kwargs)
