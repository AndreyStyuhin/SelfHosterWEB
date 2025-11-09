from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Установка переменной окружения для settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SelfHosterWEB.settings')

app = Celery('SelfHosterWEB')

# Загрузка конфигурации из settings с префиксом CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Авто-обнаружение задач в приложениях
app.autodiscover_tasks()

