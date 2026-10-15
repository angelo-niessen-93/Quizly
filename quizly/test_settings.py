"""Isolated tests without external credentials or an HTTPS requirement."""

import os

os.environ['DJANGO_SECRET_KEY'] = (
    'test-only-key-never-use-for-deployment-123456'
)

from .settings import *  # noqa: E402,F403

SECURE_SSL_REDIRECT = False
LOCAL_FRONTEND_CSRF_COMPATIBILITY = False
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': []}  # noqa: F405
