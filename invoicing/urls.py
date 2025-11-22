# invoicing/urls.py
from django.urls import path
from . import views
from .views import dashboard, create_invoice
from .views import (
    contractors_dashboard, create_contractor, edit_contractor, delete_contractor
)
from .views import get_organization_info # Не забудьте импортировать

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('invoices/create/', create_invoice, name='create_invoice'),
    path('contractors/', contractors_dashboard, name='contractors_dashboard'),
    path('contractors/create/', create_contractor, name='create_contractor'),
    path('contractors/<int:pk>/edit/', edit_contractor, name='edit_contractor'),
    path('contractors/<int:pk>/delete/', delete_contractor, name='delete_contractor'),
    path('invoices/<int:pk>/edit/', views.edit_invoice, name='edit_invoice'),
    path('invoices/<int:pk>/delete/', views.delete_invoice, name='delete_invoice'),
    path('api/get-org-info/', get_organization_info, name='get_org_info'),
]