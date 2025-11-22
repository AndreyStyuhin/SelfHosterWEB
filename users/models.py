from django.db import models
from django.conf import settings
from django_cryptography.fields import encrypt


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    # Добавлено ФИО
    fio = models.CharField(max_length=255, verbose_name="ФИО")

    # ИНН самого самозанятого
    inn = models.CharField(max_length=12, unique=True, verbose_name="ИНН (ваш)")

    # Банковские реквизиты для подстановки в счет
    bank_account = models.CharField(max_length=20, verbose_name="Расчетный счет")
    bank_name = models.CharField(max_length=255, verbose_name="Название банка")
    bank_bic = models.CharField(max_length=9, verbose_name="БИК банка")

    # Поля для интеграции с ФНС (используем django-cryptography)
    fns_access_token = encrypt(models.CharField(max_length=1000, blank=True, null=True))
    fns_refresh_token = encrypt(models.CharField(max_length=1000, blank=True, null=True))
    fns_integration_status = models.BooleanField(default=False)
    fns_last_error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.fio} ({self.user.email})"