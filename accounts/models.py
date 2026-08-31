from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        EMPLOYER = "EMPLOYER", "Employer"
        CANDIDATE = "CANDIDATE", "Candidate"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.email
