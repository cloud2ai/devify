from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


_ENCRYPTED_PREFIX = 'fernet:'


def _build_fernet() -> Fernet:
    secret_key = getattr(settings, 'SECRET_KEY', '')
    if not secret_key:
        raise ImproperlyConfigured('SECRET_KEY is required to encrypt billing secrets')
    digest = hashlib.sha256(secret_key.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def decrypt_billing_secret(value: str | None) -> str:
    if value in (None, ''):
        return ''
    value = str(value)
    if not value.startswith(_ENCRYPTED_PREFIX):
        return value
    token = value[len(_ENCRYPTED_PREFIX):].encode('ascii')
    try:
        return _build_fernet().decrypt(token).decode('utf-8')
    except InvalidToken as exc:
        raise ValueError('Unable to decrypt billing secret') from exc


def encrypt_billing_secret(value: str | None) -> str:
    if value in (None, ''):
        return ''
    value = str(value)
    if value.startswith(_ENCRYPTED_PREFIX):
        return value
    token = _build_fernet().encrypt(value.encode('utf-8')).decode('ascii')
    return f'{_ENCRYPTED_PREFIX}{token}'


class EncryptedTextField(models.TextField):
    """
    Transparent-at-rest encryption for sensitive billing secrets.
    """

    def from_db_value(self, value, expression, connection):
        return decrypt_billing_secret(value)

    def to_python(self, value):
        if value is None:
            return value
        return decrypt_billing_secret(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_billing_secret(value)
