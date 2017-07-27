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

    class Meta:
        verbose_name = 'other entry'
        verbose_name_plural = 'other entries'
        ordering = ['pk']

    def __str__(self):
        return self.char_field


class SwappableLogModel(SimpleLogAbstract):
    pass


class CustomLogModel(SimpleLogAbstract):
    pass


class BadLogModel(models.Model):
    pass


class CustomSerializer(ModelSerializer):
    pass
