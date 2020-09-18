from django.db.models import ManyToManyField


try:
    from django.db.models import JSONField
except ImportError:
    # Django < 4.0
    from django.contrib.postgres.fields.jsonb import JSONField


class SimpleManyToManyField(ManyToManyField):
    def deconstruct(self):
        name, path, args, kwargs = super(
            SimpleManyToManyField, self
        ).deconstruct()
        kwargs['to'] = 'self'
        return name, path, args, kwargs


class SimpleJSONField(JSONField):
    pass
