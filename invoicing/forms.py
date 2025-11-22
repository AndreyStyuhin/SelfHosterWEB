# invoicing/forms.py
from django import forms
from .models import Invoice, Contractor

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['contractor', 'services']
        widgets = {
            'services': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_number(self):
        number = self.cleaned_data.get('number')
        if self.user:
            if Invoice.objects.filter(user=self.user, number=number).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(f"Счёт с номером {number} уже существует.")
        return number



class ContractorForm(forms.ModelForm):
    class Meta:
        model = Contractor
        fields = ['inn', 'kpp', 'name', 'legal_address', 'bank_details']  # Исключаем owner и last_egrul_update (авто)
        widgets = {
            'bank_details': forms.Textarea(attrs={'rows': 3}),  # Для JSON-поля
            'legal_address': forms.Textarea(attrs={'rows': 3}),
        }