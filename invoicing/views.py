from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.contrib import messages
import json

from .models import Contractor, Invoice
from .forms import ContractorForm, InvoiceForm
from .utils import get_next_invoice_number
from django.http import JsonResponse
from django.conf import settings
from dadata import Dadata


@login_required
def dashboard(request):
    # 1. Базовый QuerySet
    invoices_qs = Invoice.objects.filter(user=request.user).order_by('-date', '-number')

    # 2. Логика фильтрации
    status_filter = request.GET.get('status')
    valid_statuses = Invoice.InvoiceStatus.values
    if status_filter in valid_statuses:
        invoices_qs = invoices_qs.filter(status=status_filter)

    # 3. Аналитика
    end = datetime.now()
    start = end - timedelta(days=365)
    monthly_totals = (
        Invoice.objects.filter(user=request.user, date__range=[start, end])
        .exclude(status=Invoice.InvoiceStatus.CANCELLED)
        .exclude(status=Invoice.InvoiceStatus.DRAFT)
        .annotate(
            year=ExtractYear('date'),
            month=ExtractMonth('date')
        )
        .values('year', 'month')
        .annotate(total=Sum('total_amount'))
        .order_by('year', 'month')
    )

    datapoints = [
        {"label": f"{item['year']}-{item['month']:02d}", "y": float(item["total"] or 0)}
        for item in monthly_totals
    ]

    context = {
        'invoices': invoices_qs,
        'datapoints': datapoints,
        'current_status': status_filter,
        'statuses': Invoice.InvoiceStatus
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
            if 'save_draft' in request.POST:
                invoice.status = Invoice.InvoiceStatus.DRAFT
                success_msg = "Счёт сохранен как черновик."
            elif 'save_unpaid' in request.POST:
                invoice.status = Invoice.InvoiceStatus.UNPAID
                success_msg = f"Счёт выставлен и ожидает оплаты."
            else:
                # Fallback
                invoice.status = Invoice.InvoiceStatus.DRAFT
                success_msg = "Счёт сохранен."

            # Попытка сохранения с генерацией номера (защита от гонки)
            saved = False
            for attempt in range(5):
                if not invoice.number:
                    invoice.number = get_next_invoice_number(request.user)
                try:
                    with transaction.atomic():
                        invoice.save()
                        saved = True
                        break
                except IntegrityError:
                    invoice.number = ""  # сброс для новой генерации
                    continue

            if saved:
                messages.success(request, success_msg)
                return redirect('dashboard')
            else:
                form.add_error(None, "Не удалось создать счёт (ошибка уникальности номера). Попробуйте снова.")
    else:
        form = InvoiceForm(user=request.user)

    # Передаем next_number и для GET, и для POST (если форма невалидна)
    return render(request, 'invoicing/create_invoice.html', {
        'form': form,
        'next_number': get_next_invoice_number(request.user)
    })


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

            invoice.save()
            messages.success(request, "Счёт обновлен.")
            return redirect('dashboard')
    else:
        # 🔥 НОРМАЛИЗАЦИЯ services (desc → name) для старых записей
        try:
            services_data = invoice.services
            # Если вдруг в базе строка вместо списка (бывает при миграциях)
            if isinstance(services_data, str):
                services_data = json.loads(services_data)
        except Exception:
            services_data = []

        if isinstance(services_data, list):
            for s in services_data:
                if isinstance(s, dict) and "desc" in s and "name" not in s:
                    s["name"] = s["desc"]

        # Записываем нормализованные данные в initial формы
        initial = {"services": services_data}
        form = InvoiceForm(instance=invoice, user=request.user, initial=initial)

    return render(request, 'invoicing/edit_invoice.html', {
        'form': form,
        'invoice': invoice
    })


@login_required
def delete_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, "Счёт удален.")
        return redirect('dashboard')
    return render(request, 'invoicing/delete_invoice.html', {'invoice': invoice})


# --- CONTRACTOR VIEWS ---

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


@login_required
def get_organization_info(request):
    """
    API-proxy для получения данных об организации по ИНН через DaData.
    """
    inn = request.GET.get('inn')

    if not inn:
        return JsonResponse({'error': 'ИНН не указан'}, status=400)

    if not getattr(settings, 'DADATA_API_KEY', None):
        return JsonResponse({'error': 'API ключ DaData не настроен на сервере'}, status=500)

    try:
        dadata = Dadata(settings.DADATA_API_KEY)
        # find_by_id ищет и по ИНН
        result = dadata.find_by_id("party", inn)

        if not result:
            return JsonResponse({'error': 'Организация не найдена'}, status=404)

        data = result[0]['data']
        value = result[0]['value']  # Полное наименование или краткое одной строкой

        # Собираем ответ
        response_data = {
            'name': value,  # Или data['name']['short_with_opf'] если нужно краткое
            'kpp': data.get('kpp', ''),  # У ИП нет КПП
            'legal_address': data['address']['value'] if 'address' in data else '',
            # Можно добавить ОГРН, директора и т.д., если расширите модель
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)