# (Предполагается, что вы используете встроенную User от Django)
from django.db import models
from django.conf import settings
from cryptography.fields import EncryptedCharField

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    # ИНН самого самозанятого
    inn = models.CharField(max_length=12, unique=True, verbose_name="ИНН (ваш)")
    # Банковские реквизиты для подстановки в счет
    bank_account = models.CharField(max_length=20, verbose_name="Расчетный счет")
    bank_name = models.CharField(max_length=255, verbose_name="Название банка")
    bank_bic = models.CharField(max_length=9, verbose_name="БИК банка")
    # Поля для интеграции с ФНС
    fns_access_token = EncryptedCharField(max_length=1000, blank=True, null=True)
    fns_refresh_token = EncryptedCharField(max_length=1000, blank=True, null=True)
    fns_integration_status = models.BooleanField(default=False)
    fns_last_error = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.email


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

    # Банковские реквизиты (можно вынести в отдельную модель,
    # но для MVP можно хранить и здесь, если у них обычно один счет)
    bank_account = models.CharField(max_length=20, blank=True, null=True, verbose_name="Счет")
    bank_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Банк")
    bank_bic = models.CharField(max_length=9, blank=True, null=True, verbose_name="БИК")

    # Для Фазы 2: отслеживание обновлений из ЕГРЮЛ
    last_egrul_update = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        # У одного пользователя не может быть двух контрагентов с одинаковым ИНН
        unique_together = ('owner', 'inn')

    def __str__(self):
        return self.name


class Invoice(models.Model):
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Черновик'
        UNPAID = 'UNPAID', 'Неоплачен'
        PAID = 'PAID', 'Оплачен'
        ISSUED = 'ISSUED', 'Чек выдан' # <-- НАШ НОВЫЙ СТАТУС
        CANCELLED = 'CANCELLED', 'Отменен'

    # К кому относится
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    # Кому выставляем
    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.PROTECT,  # Защищаем от удаления, если есть счета
        related_name='invoices'
    )

    # Реквизиты счета
    number = models.CharField(max_length=50, verbose_name="Номер счета")
    date = models.DateField(auto_now_add=True, verbose_name="Дата выставления")
    status = models.CharField(
        max_length=10,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True  # Ускоряем фильтрацию по статусу
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Итоговая сумма"
    )

    # Позиции счета (услуги/товары)
    # JSONB - идеальное решение для Postgres, чтобы не создавать лишнюю таблицу
    services = models.JSONField(
        default=list,
        verbose_name="Позиции счета"
        # Пример: [{'name': 'Дизайн сайта', 'qty': 1, 'price': 50000}]
    )

    class Meta:
        # У одного пользователя не может быть двух счетов с одним номером
        unique_together = ('user', 'number')
        ordering = ['-date', '-number']  # Сортировка по умолчанию

    def __str__(self):
        return f"Счет №{self.number} от {self.date}"

    def calculate_total(self):
        # Метод для авто-подсчета суммы на основе JSON-поля
        total = sum(item.get('qty', 0) * item.get('price', 0) for item in self.services)
        self.total_amount = total
        # self.save() # (Сохранять будем на уровне API)


class Receipt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Связь со счетом (ключевое поле!)
    # null=True: Чек может быть "непривязанным"
    # OneToOneField: Один чек может относиться только к одному счету
    invoice = models.OneToOneField(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Данные из ФНС
    fns_id = models.CharField(max_length=255, unique=True, db_index=True) # Уникальный ID чека из ФНС
    check_link = models.URLField(max_length=500)
    receipt_data = models.JSONField() # Полный JSON-ответ от ФНС

    # Данные для мэтчинга (дублируем для быстрого поиска)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_inn = models.CharField(max_length=12, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Чек {self.fns_id} на {self.total_amount}"