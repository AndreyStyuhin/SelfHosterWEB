# invoicing/forms.py
from django import forms
from .models import Invoice, Contractor

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['contractor', 'number', 'services']  # Добавьте другие поля по необходимости
        widgets = {
            'services': forms.Textarea(attrs={'rows': 4}),  # Для JSON-поля, но лучше использовать JSONWidget если нужно
        }


class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = ['inn', 'kpp', 'name', 'legal_address', 'bank_details']  # Исключаем owner и last_egrul_update (авто)
        widgets = {
            'bank_details': forms.Textarea(attrs={'rows': 3}),  # Для JSON-поля
            'legal_address': forms.Textarea(attrs={'rows': 3}),
        }