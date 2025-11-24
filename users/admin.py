from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'fio', 'inn', 'fns_integration_status')
    search_fields = ('user__email', 'fio', 'inn')

    # Явно перечисляем все поля, включая поля для ФНС (которые хранятся зашифрованными)
    fields = (
        'user',
        'fio',
        'inn',
        'bank_account',
        'bank_name',
        'bank_bic',
        'fns_access_token',
        'fns_refresh_token',
        'fns_integration_status',
        'fns_last_error'
    )