## File: invoicing/models.py
from django.db import models
from django.conf import settings
from django_cryptography.fields import encrypt # Убедитесь, что это установлено, судя по исходному коду

class Contractor(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contractors'
    )
    inn = models.CharField(max_length=12, verbose_name="ИНН")
    kpp = models.CharField(max_length=9, blank=True, null=True, verbose_name="КПП")
    name = models.CharField(max_length=500, verbose_name="Наименование")
    legal_address = models.TextField(blank=True, null=True, verbose_name="Юр. адрес")
    bank_details = models.JSONField(default=dict, blank=True, null=True, verbose_name="Банковские реквизиты")
    last_egrul_update = models.DateTimeField(auto_now_add=True, verbose_name="Дата обновления")

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

    # --- Новые поля для интеграции с ФНС ---
    fns_invoice_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID счета в ФНС")
    fns_invoice_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на оплату ФНС")

    class Meta:
        unique_together = ('user', 'number')
        ordering = ['-date', '-number']

    def __str__(self):
        return f"Счет №{self.number} от {self.date}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.number:
            # Простая генерация, основная логика в views
            pass
        super().save(*args, **kwargs)

    def calculate_total(self):
        if isinstance(self.services, list):
            total = sum(
                (float(item.get('qty', 0)) * float(item.get('price', 0)))
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
        related_name='associated_check'
    )
    fns_check_id = models.CharField(max_length=255, unique=True, db_index=True)
    check_link = models.URLField(max_length=500)
    check_data = models.JSONField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_inn = models.CharField(max_length=12, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Чек {self.fns_check_id} на {self.total_amount}"