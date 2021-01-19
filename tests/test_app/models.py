from django.db import models

from simple_log.models import ModelSerializer, SimpleLogAbstract


class TestModel(models.Model):
    ONE = 1
    TWO = 2
    CHOICES = (
        (ONE, 'One'),
        (TWO, 'Two'),
    )

    char_field = models.CharField(
        verbose_name='Char field', max_length=100, blank=True
    )
    fk_field = models.ForeignKey(
        'test_app.OtherModel',
        verbose_name='Fk field',
        related_name='test_entries_fk',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    m2m_field = models.ManyToManyField(
        'test_app.OtherModel',
        verbose_name='M2m field',
        related_name='test_entries_m2m',
        blank=True,
    )
    choice_field = models.PositiveSmallIntegerField(
        verbose_name='Choice field',
        choices=CHOICES,
        default=ONE,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'test entry'
        verbose_name_plural = 'test entries'
        ordering = ['pk']

    def __str__(self):
        return self.char_field


class TestModelProxy(TestModel):
    class Meta:
        proxy = True


class OtherModel(models.Model):
    char_field = models.CharField(verbose_name='Char field', max_length=100)
    m2m_field = models.ManyToManyField('test_app.TestModel', blank=True)
    date_field = models.DateField(
        verbose_name='Date field', blank=True, null=True
    )
    date_time_field = models.DateTimeField(
        verbose_name='Date time field', blank=True, null=True
    )
    time_field = models.TimeField(
        verbose_name='Time field', blank=True, null=True
    )

    class Meta:
        verbose_name = 'other entry'
        verbose_name_plural = 'other entries'
        ordering = ['pk']

    def __str__(self):
        return self.char_field


class ThirdModel(models.Model):
    char_field = models.CharField(verbose_name='Char field', max_length=100)

    class Meta:
        verbose_name = 'third entry'
        verbose_name_plural = 'third entries'
        ordering = ['pk']

    def __str__(self):
        return self.char_field


class RelatedModel(models.Model):
    third_model = models.ForeignKey(
        ThirdModel, related_name='related_entries', on_delete=models.CASCADE
    )
    char_field = models.CharField(verbose_name='Char field', max_length=100)

    parent_model_fields = ('third_model',)

    class Meta:
        verbose_name = 'related entry'
        verbose_name_plural = 'related entries'
        ordering = ['pk']

    def __str__(self):
        return 'Related entry of the "{}"'.format(self.third_model)


class SwappableLogModel(SimpleLogAbstract):
    pass


class BadLogModel(models.Model):
    def __str__(self):
        return str(self.pk)


class CustomSerializer(ModelSerializer):
    pass
