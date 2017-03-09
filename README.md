# Django simple log
[![Build Status](https://travis-ci.org/kindlycat/django-simple-log.svg?branch=master)](https://travis-ci.org/kindlycat/django-simple-log)
[![Coverage Status](https://coveralls.io/repos/github/kindlycat/django-simple-log/badge.svg?branch=master)](https://coveralls.io/github/kindlycat/django-simple-log?branch=master)
[![PyPI](https://img.shields.io/pypi/v/django-simple-log.svg)](https://pypi.python.org/pypi/django-simple-log)
[![PyPI](https://img.shields.io/pypi/status/django-simple-log.svg)]()
[![PyPI](https://img.shields.io/pypi/pyversions/django-simple-log.svg)](https://pypi.python.org/pypi/django-simple-log)
[![Django](https://img.shields.io/badge/django-1.9%2C%201.10-green.svg)](https://pypi.python.org/pypi/django-simple-log)

Log model changes on every create/update/delete.

## TL;DR
Add to installed apps:
```python
INSTALLED_APPS = (
    ...
    'simple_log',
    ...
)
```

Add middleware for detecting user:
```python
MIDDLEWARE = [
    ...
    'simple_log.middleware.ThreadLocalMiddleware',
    ...
]
```

Usage:
```python
import simple_log

simple_log.register()
```

Create Simple Log model:
```python
python manage.py migrate
```

That's all. Now simple log will detect all changes and save old and
new values.

## TODO:
- Docs
- Tests
