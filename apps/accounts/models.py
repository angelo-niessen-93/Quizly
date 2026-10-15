"""Database-enforced unique user identities."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    email = models.EmailField(unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower('email'), name='unique_email_lower')
        ]
