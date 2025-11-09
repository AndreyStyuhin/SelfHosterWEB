import pytest
from model_bakery import baker
from invoicing.models import Invoice
# Маркер, который говорит "этот тест требует доступа к Базе Данных"
pytestmark = pytest.mark.django_db
def test_user_can_only_see_their_own_invoices(authenticated_client, user):
    """
    Тест: Пользователь видит только свои счета и не видит чужие.
    """
    # 1. Создаем "чужого" пользователя
    other_user = baker.make('auth.User')
    # 2. Создаем 2 счета: один "наш", один "чужой"
    baker.make(Invoice, user=user, number="INV-001") # "Наш" счет
    baker.make(Invoice, user=other_user, number="INV-002") # "Чужой" счет
    # 3. Делаем запрос от имени "нашего" пользователя (из фикстуры)
    response = authenticated_client.get('/api/invoices/')
    # 4. Проверяем
    assert response.status_code == 200
    assert len(response.data) == 1 # Должен вернуться только 1 счет
    assert response.data[0]['number'] == "INV-001" # И это должен быть "наш" счет
def test_invoice_pdf_generation(authenticated_client, user):
    """
    Тест: Эндпоинт PDF отдает правильный тип контента.
    """
    # 1. Создаем счет, принадлежащий пользователю
    invoice = baker.make(Invoice, user=user, number="PDF-001")
    # 2. Делаем запрос к эндпоинту PDF
    url = f'/api/invoices/{invoice.id}/pdf/'
    response = authenticated_client.get(url)
    # 3. Проверяем
    assert response.status_code == 200
    # Проверяем, что это действительно PDF
    assert response.headers['Content-Type'] == 'application/pdf'
    # Проверяем, что файл скачивается с правильным именем
    assert 'attachment; filename=' in response.headers['Content-Disposition']
    assert 'PDF-001.pdf' in response.headers['Content-Disposition']
    # Проверяем "магические байты" PDF
    assert response.content.startswith(b'%PDF-')
