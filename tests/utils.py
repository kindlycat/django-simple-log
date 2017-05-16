from contextlib import contextmanager


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
