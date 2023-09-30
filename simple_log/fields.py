from django.db.models import JSONField, ManyToManyField


class SimpleManyToManyField(ManyToManyField):
    def deconstruct(self):
        name, path, args, kwargs = super(
            SimpleManyToManyField, self
        ).deconstruct()
        kwargs['to'] = 'self'
        return name, path, args, kwargs


class SimpleJSONField(JSONField):
    pass
