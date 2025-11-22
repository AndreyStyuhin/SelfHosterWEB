# invoicing/utils.py
from .models import Invoice

def get_next_invoice_number(user):
    """Возвращает следующий номер счёта в формате 0001, 0002 и т.д."""
    last = (
        Invoice.objects
        .filter(user=user)
        .order_by('-id')
        .first()
    )
    if last and last.number.isdigit():
        next_num = int(last.number) + 1
    else:
        next_num = 1
    return f"{next_num:04d}"
