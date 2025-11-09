# invoicing/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from datetime import datetime, timedelta
from .models import Invoice
from .forms import InvoiceForm  # Создадим форму ниже
from django.contrib.auth.decorators import login_required
from .models import Contractor
from .forms import ContractorForm

@login_required
def dashboard(request):
    # Список всех счетов пользователя
    invoices = Invoice.objects.filter(user=request.user).order_by('-date')

    # Аналитика: сумма по месяцам за год
    end = datetime.now()
    start = end - timedelta(days=365)
    monthly_totals = (
        Invoice.objects.filter(user=request.user, date__range=[start, end])
        .annotate(
            year=ExtractYear('date'),
            month=ExtractMonth('date')
        )
        .values('year', 'month')
        .annotate(total=Sum('total_amount'))
        .order_by('year', 'month')
    )
    datapoints = [{"label": f"{item['year']}-{item['month']:02d}", "y": float(item["total"] or 0)} for item in
                  monthly_totals]
    context = {'invoices': invoices, 'datapoints': datapoints}
    return render(request, 'invoicing/dashboard.html', context)

@login_required
def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.calculate_total()  # Вызов метода из модели
            invoice.save()
            return redirect('dashboard')
    else:
        form = InvoiceForm()
    return render(request, 'invoicing/create_invoice.html', {'form': form})

@login_required
def contractors_dashboard(request):
    # Список контрагентов только текущего пользователя
    contractors = Contractor.objects.filter(owner=request.user).order_by('name')
    context = {'contractors': contractors}
    return render(request, 'invoicing/contractors_dashboard.html', context)

@login_required
def create_contractor(request):
    if request.method == 'POST':
        form = ContractorForm(request.POST)
        if form.is_valid():
            contractor = form.save(commit=False)
            contractor.owner = request.user
            contractor.save()
            return redirect('contractors_dashboard')
    else:
        form = ContractorForm()
    return render(request, 'invoicing/create_contractor.html', {'form': form})

@login_required
def edit_contractor(request, pk):
    contractor = get_object_or_404(Contractor, pk=pk, owner=request.user)  # Только свои
    if request.method == 'POST':
        form = ContractorForm(request.POST, instance=contractor)
        if form.is_valid():
            form.save()
            return redirect('contractors_dashboard')
    else:
        form = ContractorForm(instance=contractor)
    return render(request, 'invoicing/edit_contractor.html', {'form': form})

@login_required
def delete_contractor(request, pk):
    contractor = get_object_or_404(Contractor, pk=pk, owner=request.user)
    if request.method == 'POST':
        contractor.delete()
        return redirect('contractors_dashboard')
    return render(request, 'invoicing/delete_contractor.html', {'contractor': contractor})