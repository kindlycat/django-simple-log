# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from distutils.core import setup
from setuptools import find_packages

setup(
    name='django-simple-log',
    version='0.0.1',
    description='Logging django models changes.',
    author='Grigory Mishchenko',
    author_email='grishkokot@gmail.com',

    packages=find_packages(exclude=('manage', 'tests', 'tests.*')),
    include_package_data=True,

    install_requires=['Django>=1.10'],
)
