import setuptools

from simple_log import __version__


def readme():
    with open('README.rst') as f:
        return f.read()


setuptools.setup(
    name='django-simple-log',
    version=__version__,
    description='Logging django models changes.',
    long_description=readme(),
    keywords=['django', 'log', 'audit', 'history'],
    author='Grigory Mishchenko',
    author_email='grishkokot@gmail.com',
    url='https://github.com/kindlycat/django-simple-log/',
    packages=setuptools.find_packages(exclude=('manage', 'tests', 'tests.*')),
    include_package_data=True,
    install_requires=['Django>=2.2', 'django-request-vars>=1.0.1'],
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'License :: OSI Approved :: BSD License',
    ],
)
