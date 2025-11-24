## File: invoicing/fns_api.py
import json

import requests
import logging
from datetime import timedelta, datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


class FNSIntegrationError(Exception):
    """Кастомная ошибка интеграции с ФНС"""
    pass


class FNSService:
    # Базовый URL API для самозанятых (Web версия lknpd)
    BASE_URL = "https://lknpd.nalog.ru/api/v1"

    def __init__(self, user):
        self.user = user
        # Проверяем наличие профиля и токена
        if not hasattr(user, 'profile') or not user.profile.fns_access_token:
            raise FNSIntegrationError("У пользователя не настроена интеграция с ФНС (нет токена).")

        self.token = user.profile.fns_access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (SelfHosterWEB/1.0)',
            'Authorization': f'Bearer {self.token}'
        })

    def create_invoice(self, invoice):
        """
        Регистрирует счет (Invoice) в системе Мой Налог.
        Возвращает кортеж (invoice_id, invoice_url).
        """
        url = f"{self.BASE_URL}/invoice"

        # Формируем список позиций в формате ФНС
        items = []
        for svc in invoice.services:
            name = svc.get('name', svc.get('desc', 'Услуга'))
            qty = float(svc.get('qty', 1))
            price = float(svc.get('price', 0))
            amount = qty * price

            items.append({
                "name": name,
                "price": price,
                "quantity": qty,
                "sum": amount,
                "unit": "шт"  # Можно сделать настраиваемым, если нужно
            })

        # Данные покупателя (контрагента)
        client = {
            "inn": invoice.contractor.inn,
            "displayName": invoice.contractor.name,
        }

        payload = {
            "invoiceNumber": invoice.number,
            "invoiceDate": invoice.date.strftime("%Y-%m-%d"),
            # Дата платежа (обязательна для JSON, поставим +3 дня или текущую)
            "paymentDate": (timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "currency": "RUB",
            "totalAmount": float(invoice.total_amount),
            "client": client,
            "items": items,
            "description": f"Счет №{invoice.number} от {invoice.date.strftime('%d.%m.%Y')}"
        }

        logger.info(f"FNS Payload for {invoice.number}: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(url, json=payload)

            if response.status_code == 401:
                raise FNSIntegrationError("Ошибка авторизации ФНС (401). Токен истек.")

            if response.status_code not in [200, 201]:
                # Пытаемся распарсить ошибку
                try:
                    err_json = response.json()
                    err_msg = err_json.get('message', response.text)
                except:
                    err_msg = response.text

                logger.error(f"FNS Error for Invoice {invoice.number}: {err_msg}")
                raise FNSIntegrationError(f"ФНС вернула ошибку: {err_msg}")

            data = response.json()
            fns_id = data.get('id')

            # ФНС API не всегда явно возвращает URL счета в ответе POST /invoice,
            # но его можно сформировать или взять из ответа, если он там есть.
            # Для lknpd.nalog.ru ссылка обычно такая (для плательщика):
            # https://lknpd.nalog.ru/api/v1/invoice/{id}/print (или pdf)
            # Но для оплаты клиентом ссылка может генерироваться отдельно.
            # Пока сохраним ID.

            return fns_id, None

        except requests.RequestException as e:
            raise FNSIntegrationError(f"Ошибка сети: {str(e)}")