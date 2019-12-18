from simple_log.utils import ContextDecorator


class noop_ctx(ContextDecorator):
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_value, traceback):
        return False
