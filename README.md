# Django simple log
Log model changes on every create/update/delete.

Working with python3.5+ and django1.10. Other version is planned.

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
- python2.7+ support
- django1.8+ support
