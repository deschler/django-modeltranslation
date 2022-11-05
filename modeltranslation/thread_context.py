import threading

from modeltranslation import settings


class ModelTranslationThreadLocal(threading.local):
    """Holds thread-local data for modeltranslation."""
    auto_populate = None
    enable_fallbacks = None


_mt_thread_context = ModelTranslationThreadLocal()


def set_auto_populate(value):
    """Set the auto_populate for the current thread."""
    _mt_thread_context.auto_populate = value


def set_enable_fallbacks(value):
    """Set the enable_fallbacks for the current thread."""
    _mt_thread_context.enable_fallbacks = value


def auto_populate_mode():
    """Return the auto_populate mode for the current thread."""
    auto_populate = _mt_thread_context.auto_populate

    if auto_populate is not None:
        return auto_populate

    return settings.AUTO_POPULATE


def fallbacks_enabled():
    """Return whether fallbacks are enabled for the current thread."""
    enable_fallbacks = _mt_thread_context.enable_fallbacks

    if enable_fallbacks is not None:
        return enable_fallbacks

    return settings.ENABLE_FALLBACKS
