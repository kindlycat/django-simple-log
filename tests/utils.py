from simple_log.utils import ContextDecorator, disable_logging, disable_related


class noop_ctx(ContextDecorator):
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def get_ctx(is_disable_logging, is_disable_related):
    dl = disable_logging if is_disable_logging else noop_ctx
    dr = disable_related if is_disable_related else noop_ctx
    return dl, dr
