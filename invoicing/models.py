from django.db import models
from django.conf import settings
from django_cryptography.fields import encrypt  # Вместо EncryptedCharField

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    # Добавлено ФИО согласно заданию
    fio = models.CharField(max_length=255, verbose_name="ФИО")
    # ИНН самого самозанятого
    inn = models.CharField(max_length=12, unique=True, verbose_name="ИНН (ваш)")
    # Банковские реквизиты для подстановки в счет
    bank_account = models.CharField(max_length=20, verbose_name="Расчетный счет")
    bank_name = models.CharField(max_length=255, verbose_name="Название банка")
    bank_bic = models.CharField(max_length=9, verbose_name="БИК банка")
    # Поля для интеграции с ФНС
    fns_access_token = encrypt(models.CharField(max_length=1000, blank=True, null=True))
    fns_refresh_token = encrypt(models.CharField(max_length=1000, blank=True, null=True))
    fns_integration_status = models.BooleanField(default=False)
    fns_last_error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.fio} ({self.user.email})"

class Contractor(models.Model):
    # У какого пользователя этот контрагент
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contractors'
    )
    # Основные реквизиты
    inn = models.CharField(max_length=12, verbose_name="ИНН")
    kpp = models.CharField(max_length=9, blank=True, null=True, verbose_name="КПП")
    name = models.CharField(max_length=500, verbose_name="Наименование")
    # Реквизиты, которые мы подтянем из DaData/ЕГРЮЛ
    legal_address = models.TextField(blank=True, null=True, verbose_name="Юр. адрес")
    # Банковские реквизиты (по заданию — JSONB)
    bank_details = models.JSONField(default=dict, blank=True, null=True, verbose_name="Банковские реквизиты")

    # Для Фазы 2: отслеживание обновлений из ЕГРЮЛ
    last_egrul_update = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        unique_together = ('owner', 'inn')

    def __str__(self):
        return self.name

class Invoice(models.Model):
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Черновик'
        UNPAID = 'UNPAID', 'Неоплачен'
        PAID = 'PAID', 'Оплачен'
        ISSUED = 'ISSUED', 'Чек выдан'
        CANCELLED = 'CANCELLED', 'Отменен'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    number = models.CharField(max_length=50, verbose_name="Номер счета")
    date = models.DateField(auto_now_add=True, verbose_name="Дата выставления")
    status = models.CharField(
        max_length=10,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True
    )
    def save(self, *args, **kwargs):
        # Автоматическая генерация номера только при создании
        if not self.pk and not self.number:
            last_invoice = Invoice.objects.filter(user=self.user).order_by('-number').first()
            if last_invoice and last_invoice.number.isdigit():
                next_num = int(last_invoice.number) + 1
            else:
                next_num = 1
            self.number = f"{next_num:04d}"  # например, 0001, 0002, 0003
        super().save(*args, **kwargs)

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Итоговая сумма"
    )
    services = models.JSONField(
        default=list,
        verbose_name="Позиции счета"
    )

    class Meta:
        unique_together = ('user', 'number')
        ordering = ['-date', '-number']

    def __str__(self):
        return f"Счет №{self.number} от {self.date}"

    def calculate_total(self):
        if isinstance(self.services, list):
            total = sum(
                (item.get('qty', 0) * item.get('price', 0))
                for item in self.services
                if isinstance(item, dict)
            )
            self.total_amount = total
        else:
            self.total_amount = 0


class Check(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    invoice = models.OneToOneField(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='associated_check'  # Добавьте это, чтобы избежать конфликта
    )
    fns_check_id = models.CharField(max_length=255, unique=True, db_index=True)
    check_link = models.URLField(max_length=500)
    check_data = models.JSONField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_inn = models.CharField(max_length=12, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Чек {self.fns_check_id} на {self.total_amount}"