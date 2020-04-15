import inspect
from collections import defaultdict

from request_vars.utils import del_variable, get_variable

from simple_log.conf import settings
from simple_log.utils import (
    get_log_model,
    get_obj_repr,
    is_log_needed,
    is_related_to,
    serialize_instance,
)


__all__ = [
    'log_m2m_change_handler',
    'log_pre_save_handler',
    'log_post_save_handler',
    'log_pre_delete_handler',
    'save_logs_on_commit',
    'save_related',
]


def save_related(logs):
    map_related = defaultdict(list)
    for saved_log in [x for x in logs if x.pk and not x.disable_related]:
        for related in [
            log
            for log in logs
            if not log.disable_related and is_related_to(saved_log, log)
        ]:
            if not related.pk:
                related.save()
            map_related[related].append(saved_log)
    for instance, related in map_related.items():
        instance.related_logs.add(*related)


def save_logs_on_commit():
    all_logs = get_variable('simple_log_instances', {}).values()
    for log in [x for x in all_logs if not x.pk]:
        log.old = getattr(log.instance, '_old_value', None)
        log.new = serialize_instance(log.instance)
        if log.is_delete or log.old != log.new:
            log.save()

    if settings.SAVE_RELATED and any(
        [x.pk for x in all_logs if not x.disable_related]
    ):
        save_related(all_logs)
    del_variable('simple_log_instances')


def log_pre_save_handler(sender, instance, **kwargs):
    if not is_log_needed(instance, kwargs.get('raw')):
        return
    log_model = get_log_model()
    log_model.set_initial(instance, kwargs.get('using'))


def log_post_save_handler(sender, instance, created, **kwargs):
    if not is_log_needed(instance, kwargs.get('raw')):
        return
    log_model = get_log_model()
    log_model.log(
        instance=instance,
        action_flag=log_model.ADD if created else log_model.CHANGE,
        commit=False,
        using=kwargs.get('using'),
    )


def log_pre_delete_handler(sender, instance, **kwargs):
    if not is_log_needed(instance, kwargs.get('raw')):
        return
    log_model = get_log_model()
    log_model.set_initial(instance)
    log_model.log(
        instance=instance,
        action_flag=log_model.DELETE,
        commit=False,
        object_repr=get_obj_repr(instance),
        using=kwargs.get('using'),
    )


def log_m2m_change_handler(sender, instance, action, **kwargs):
    # M2m change signal does not provide raw kwarg
    raw = False
    for fr in inspect.stack():
        if inspect.getmodulename(fr[1]) in ('test', 'loaddata'):
            raw = True
            break
    if not is_log_needed(instance, raw):
        return
    log_model = get_log_model()
    if action in ('pre_add', 'pre_remove', 'pre_clear'):
        log_model.set_initial(instance)

    if action in ('post_add', 'post_remove', 'post_clear'):
        log_model.log(
            instance=instance,
            action_flag=log_model.CHANGE,
            commit=False,
            using=kwargs.get('using'),
        )
