# invoicing/forms.py
from django import forms
from .models import Invoice, Contractor

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['contractor', 'number', 'services']
        widgets = {
            'services': forms.HiddenInput(),  # теперь скрытое поле
        }



class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = ['inn', 'kpp', 'name', 'legal_address', 'bank_details']  # Исключаем owner и last_egrul_update (авто)
        widgets = {
            'bank_details': forms.Textarea(attrs={'rows': 3}),  # Для JSON-поля
            'legal_address': forms.Textarea(attrs={'rows': 3}),
        }