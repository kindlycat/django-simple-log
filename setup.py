# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from distutils.core import setup

from setuptools import find_packages

from simple_log import __version__


def readme():
    with open('README.rst') as f:
        return f.read()


setup(
    name='django-simple-log',
    version=__version__,
    description='Logging django models changes.',
    long_description=readme(),
    keywords=['django', 'log', 'audit', 'history'],
    author='Grigory Mishchenko',
    author_email='grishkokot@gmail.com',
    url='https://github.com/kindlycat/django-simple-log/',
    packages=find_packages(exclude=('manage', 'tests', 'tests.*')),
    include_package_data=True,
    install_requires=['Django>=1.11', 'django-request-vars>=1.0.1'],
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'License :: OSI Approved :: BSD License',
    ],
)
