import os
from celery import Celery

# Указываем Django настройки по умолчанию
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SelfHosterWEB.settings')

app = Celery('SelfHosterWEB')

# Используем настройки из settings.py, начинающиеся с CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим tasks.py во всех приложениях
app.autodiscover_tasks()