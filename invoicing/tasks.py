from celery import shared_task
from .models import Invoice, Check

@shared_task
def match_check_to_invoice(check_id):
    """
    Фоновая задача: Привязка чека к счету по ИНН и сумме (логика мэтчинга из Фазы 2).
    """
    check = Check.objects.get(id=check_id)
    if check.invoice:
        return  # Уже привязан

    # Ищем подходящий счет: статус PAID, совпадение ИНН и суммы
    try:
        invoice = Invoice.objects.get(
            user=check.user,
            contractor__inn=check.customer_inn,
            total_amount=check.total_amount,
            status=Invoice.InvoiceStatus.PAID
        )
        check.invoice = invoice
        check.save()
        invoice.status = Invoice.InvoiceStatus.ISSUED
        invoice.save()
    except Invoice.DoesNotExist:
        pass  # Нет подходящего счета
    except Invoice.MultipleObjectsReturned:
        # Если несколько — не привязываем (можно добавить логику выбора)
        pass