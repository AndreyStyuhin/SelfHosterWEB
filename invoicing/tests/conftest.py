# invoicing/tests/conftest.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from model_bakery import baker

User = get_user_model()

@pytest.fixture
def user():
    """Фикстура для создания обычного пользователя."""
    return baker.make(User)

@pytest.fixture
def api_client():
    """Фикстура для создания API-клиента."""
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, user):
    """Фикстура для создания API-клиента, аутентифицированного как 'user'."""
    api_client.force_authenticate(user=user)
    return api_client