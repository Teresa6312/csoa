# myproject/celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 设置Django的设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csoa.settings')

app = Celery('csoa')

# 使用Django的设置文件进行配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务模块
app.autodiscover_tasks(['base'])


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
