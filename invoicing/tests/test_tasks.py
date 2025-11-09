import pytest
from model_bakery import baker
from invoicing.models import Invoice, Check, Contractor
from invoicing.tasks import match_check_to_invoice  # Импортируем задачу (обновлено имя)
pytestmark = pytest.mark.django_db
def test_match_check_success(user):
    """
    Тест: Задача мэтчинга успешно связывает чек и счет.
    """
    # 1. Подготовка данных
    customer_inn = "7707083893" # ИНН Сбербанка для примера
    contractor = baker.make(Contractor, owner=user, inn=customer_inn)
    invoice = baker.make(
        Invoice,
        user=user,
        contractor=contractor,
        status=Invoice.InvoiceStatus.PAID, # <- Статус "Оплачен"
        total_amount=1000.00
    )
    check = baker.make(
        Check,
        user=user,
        customer_inn=customer_inn,
        total_amount=1000.00,
        invoice=None # <- Пока не привязан!
    )
    # 2. Запускаем задачу
    # Мы вызываем ее как обычную Python-функцию (это важно для тестов)
    match_check_to_invoice(check.id)
    # 3. Обновляем объекты из БД, чтобы увидеть изменения
    invoice.refresh_from_db()
    check.refresh_from_db()
    # 4. Проверяем результат
    assert check.invoice == invoice
    assert invoice.status == Invoice.InvoiceStatus.ISSUED # <- Статус изменился!
def test_match_check_fail_wrong_status(user):
    """
    Тест: Задача НЕ связывает чек, если у счета статус 'UNPAID'.
    """
    # 1. Подготовка (почти такая же)
    customer_inn = "7707083893"
    contractor = baker.make(Contractor, owner=user, inn=customer_inn)
    invoice = baker.make(
        Invoice,
        user=user,
        contractor=contractor,
        status=Invoice.InvoiceStatus.UNPAID, # <- Статус "Не оплачен"
        total_amount=1000.00
    )
    check = baker.make(
        Check,
        user=user,
        customer_inn=customer_inn,
        total_amount=1000.00,
        invoice=None
    )
    # 2. Запуск
    match_check_to_invoice(check.id)
    # 3. Обновление
    invoice.refresh_from_db()
    check.refresh_from_db()
    # 4. Проверка (что ничего НЕ изменилось)
    assert check.invoice is None
    assert invoice.status == Invoice.InvoiceStatus.UNPAID # <- Статус НЕ изменился!
