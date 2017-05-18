from contextlib import contextmanager

from django.db.models.signals import (
    pre_save, post_save, pre_delete, post_delete, m2m_changed
)

from simple_log.signals import (
    log_pre_save_delete, log_post_save, log_post_delete, log_m2m_change
)

try:
    from django.test.utils import isolate_lru_cache
except ImportError:
    @contextmanager
    def isolate_lru_cache(lru_cache_object):
        """Clear the cache of an LRU cache object on entering and exiting."""
        lru_cache_object.cache_clear()
        try:
            yield
        finally:
            lru_cache_object.cache_clear()


@contextmanager
def disconnect_signals(sender=None):
    pre_save.disconnect(receiver=log_pre_save_delete, sender=sender)
    post_save.disconnect(receiver=log_post_save, sender=sender)
    pre_delete.disconnect(receiver=log_pre_save_delete, sender=sender)
    post_delete.disconnect(receiver=log_post_delete, sender=sender)
    m2m_changed.disconnect(receiver=log_m2m_change, sender=sender)
