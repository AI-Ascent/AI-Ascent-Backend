from django.contrib.auth.models import AbstractUser
from django.db import models

from django.contrib.postgres.fields import ArrayField


class APIUser(AbstractUser):
    email = models.EmailField(unique=True)

    feedbacks = ArrayField(models.CharField(max_length=1000))

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
