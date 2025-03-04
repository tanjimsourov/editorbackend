from django.db import models

import uuid
from django.utils.translation import gettext_lazy as _


def upload_draft(instance, filename):
    return 'draft/{filename}'.format(filename=filename)


def upload_save(instance, filename):
    return 'saved/{filename}'.format(filename=filename)


class Draft(models.Model):
    file = models.FileField(
        _("File"), upload_to=upload_draft, default='draft/default.png')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Saved(models.Model):
    file = models.FileField(
        _("File"), upload_to=upload_save, default='draft/default.png')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
