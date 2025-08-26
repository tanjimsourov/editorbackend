import uuid

from django.db import models
from django.contrib.auth.models import (
    PermissionsMixin, UserManager, AbstractBaseUser)
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import jwt
from datetime import datetime, timedelta

from django.conf import settings


class MyUserManager(UserManager):

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError('The given username must be set')

        if not email:
            raise ValueError('The given email must be set')

        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email")
        if not password:
            raise ValueError("User must have a password")

        extra_fields.setdefault('is_verified', True)

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        _('username'),
        max_length=30,
        default='',
        unique=True,  # Add this
        null=False
    )

    email = models.CharField(
        _('email'),
        max_length=25,
        default='',
        null=True
    )

    otp = models.IntegerField(null=True, blank=True)
    activation_key = models.CharField(max_length=150, blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    email_verified = models.BooleanField(
        _('email_verified'),
        default=False,
    )

    objects = MyUserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    @property
    def token(self):
        token = jwt.encode(
            {
                'username': self.username,
                'email': self.email,
                # ❌ no 'exp' field means it won't expire
            },
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        return token
