from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from .models import Contractor, Invoice
from .forms import ContractorForm, InvoiceForm
from django.db import IntegrityError, transaction
from django.contrib import messages
from .utils import get_next_invoice_number


@login_required
def dashboard(request):
    # 1. Базовый QuerySet
    invoices_qs = Invoice.objects.filter(user=request.user).order_by('-date', '-number')

    # 2. Логика фильтрации
    status_filter = request.GET.get('status')

    # Проверяем, является ли переданный статус валидным (есть ли он в choices модели)
    valid_statuses = Invoice.InvoiceStatus.values
    if status_filter in valid_statuses:
        invoices_qs = invoices_qs.filter(status=status_filter)

    # 3. Аналитика (оставляем без изменений, она считается по всем счетам или можно тоже фильтровать)
    end = datetime.now()
    start = end - timedelta(days=365)
    monthly_totals = (
        Invoice.objects.filter(user=request.user, date__range=[start, end])
        .exclude(status=Invoice.InvoiceStatus.CANCELLED)  # Исключаем отмененные из графика
        .exclude(status=Invoice.InvoiceStatus.DRAFT)  # Исключаем черновики из графика (опционально)
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

    context = {
        'invoices': invoices_qs,
        'datapoints': datapoints,
        'current_status': status_filter,  # Чтобы подсветить активную кнопку в шаблоне
        'statuses': Invoice.InvoiceStatus  # Передаем enum для использования в шаблоне
    }
    return render(request, 'invoicing/dashboard.html', context)


@login_required
def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST, user=request.user)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.calculate_total()

            # --- ЛОГИКА СТАТУСОВ ---
            # Проверяем имя нажатой кнопки
            if 'save_draft' in request.POST:
                invoice.status = Invoice.InvoiceStatus.DRAFT
                success_msg = "Счёт сохранен как черновик."
            elif 'save_unpaid' in request.POST:
                invoice.status = Invoice.InvoiceStatus.UNPAID
                success_msg = f"Счёт №{invoice.number} выставлен и ожидает оплаты."
            # -----------------------

            if request.method == 'GET':  # (Этот блок в оригинале был избыточен внутри POST, но оставим структуру)
                # ... (код пропускаем, он не должен выполняться в POST)
                pass

            for attempt in range(5):
                invoice.number = get_next_invoice_number(request.user)
                try:
                    with transaction.atomic():
                        invoice.save()
                    messages.success(request, success_msg)
                    return redirect('dashboard')
                except IntegrityError:
                    continue
            form.add_error(None, "Не удалось создать счёт — попробуйте снова.")
    else:
        form = InvoiceForm(user=request.user)
        # Передаем next_number в контекст для GET запроса
        return render(request, 'invoicing/create_invoice.html', {
            'form': form,
            'next_number': get_next_invoice_number(request.user)
        })

    return render(request, 'invoicing/create_invoice.html', {'form': form})


@login_required
def edit_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice, user=request.user)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.calculate_total()

            # --- ЛОГИКА СТАТУСОВ ---
            if 'save_draft' in request.POST:
                invoice.status = Invoice.InvoiceStatus.DRAFT
            elif 'save_unpaid' in request.POST:
                invoice.status = Invoice.InvoiceStatus.UNPAID
            # Если просто сохраняем, не меняя статус (например, редактируем описание),
            # можно добавить кнопку 'save_keep_status' или оставить логику выше.
            # Сейчас логика: любое редактирование требует выбора "Черновик" или "Выставить".
            # -----------------------

            invoice.save()
            messages.success(request, "Счёт обновлен.")
            return redirect('dashboard')
    else:
        form = InvoiceForm(instance=invoice, user=request.user)
    return render(request, 'invoicing/edit_invoice.html', {'form': form, 'invoice': invoice})


# Остальные views (delete_invoice, contractors...) оставляем без изменений
@login_required
def delete_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    if request.method == 'POST':
        invoice.delete()
        return redirect('dashboard')
    return render(request, 'invoicing/delete_invoice.html', {'invoice': invoice})


# ... (Contractor views без изменений)
@login_required
def contractors_dashboard(request):
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
    contractor = get_object_or_404(Contractor, pk=pk, owner=request.user)
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