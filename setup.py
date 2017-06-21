# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from distutils.core import setup

from setuptools import find_packages


def readme():
    with open('README.rst') as f:
        return f.read()


setup(
    name='django-simple-log',
    version='0.1.3',
    description='Logging django models changes.',
    long_description=readme(),
    keywords='django log audit history',
    author='Grigory Mishchenko',
    author_email='grishkokot@gmail.com',
    url='https://github.com/kindlycat/django-simple-log/',
    packages=find_packages(exclude=('manage', 'tests', 'tests.*')),
    include_package_data=True,
    install_requires=['Django>=1.8'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'License :: OSI Approved :: BSD License',
    ],
)
