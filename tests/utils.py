from contextlib import contextmanager

from django.db.models.signals import (
    m2m_changed, post_delete, post_save, pre_delete, pre_save
)

from simple_log.signals import (
    log_m2m_change, log_post_delete, log_post_save, log_pre_save_delete
)


@contextmanager
def disconnect_signals(sender=None):
    pre_save.disconnect(receiver=log_pre_save_delete, sender=sender)
    post_save.disconnect(receiver=log_post_save, sender=sender)
    pre_delete.disconnect(receiver=log_pre_save_delete, sender=sender)
    post_delete.disconnect(receiver=log_post_delete, sender=sender)
    m2m_changed.disconnect(receiver=log_m2m_change, sender=sender)
