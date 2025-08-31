from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from django.contrib.postgres.fields import ArrayField


class APIUserManager(UserManager):
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if password is None:
            raise ValueError("Superuser must have a password.")
        return self._create_user(email, email, password, **extra_fields)


class APIUser(AbstractUser):
    email = models.EmailField(unique=True)

    feedbacks = ArrayField(models.CharField(max_length=1000), default=list)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = APIUserManager()
