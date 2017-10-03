# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from simple_log.models import SimpleLogAbstract, ModelSerializer


@python_2_unicode_compatible
class TestModel(models.Model):
    ONE = 1
    TWO = 2
    CHOICES = (
        (ONE, 'One'),
        (TWO, 'Two'),
    )

    char_field = models.CharField(
        verbose_name='Char field',
        max_length=100,
        blank=True
    )
    fk_field = models.ForeignKey(
        'test_app.OtherModel',
        verbose_name='Fk field',
        related_name='test_entries_fk',
        null=True,
        blank=True
    )
    m2m_field = models.ManyToManyField(
        'test_app.OtherModel',
        verbose_name='M2m field',
        related_name='test_entries_m2m',
        blank=True
    )
    choice_field = models.PositiveSmallIntegerField(
        verbose_name='Choice field',
        choices=CHOICES,
        default=ONE,
        blank=True,
        null=True
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


@python_2_unicode_compatible
class OtherModel(models.Model):
    char_field = models.CharField(verbose_name='Char field', max_length=100)
    m2m_field = models.ManyToManyField(
        'test_app.TestModel',
        blank=True
    )
    date_field = models.DateField(
        verbose_name='Date field',
        blank=True,
        null=True
    )
    date_time_field = models.DateTimeField(
        verbose_name='Date time field',
        blank=True,
        null=True
    )
    time_field = models.TimeField(
        verbose_name='Time field',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'other entry'
        verbose_name_plural = 'other entries'
        ordering = ['pk']

    def __str__(self):
        return self.char_field


@python_2_unicode_compatible
class ThirdModel(models.Model):
    char_field = models.CharField(verbose_name='Char field', max_length=100)

    class Meta:
        verbose_name = 'third entry'
        verbose_name_plural = 'third entries'
        ordering = ['pk']

    def __str__(self):
        return self.char_field


@python_2_unicode_compatible
class RelatedModel(models.Model):
    third_model = models.ForeignKey(ThirdModel, related_name='related_entries')
    char_field = models.CharField(verbose_name='Char field', max_length=100)

    class Meta:
        verbose_name = 'related entry'
        verbose_name_plural = 'related entries'
        ordering = ['pk']

    def __str__(self):
        return 'Related entry of the "%s"' % self.third_model


class SwappableLogModel(SimpleLogAbstract):
    pass


class BadLogModel(models.Model):
    pass


class CustomSerializer(ModelSerializer):
    pass
