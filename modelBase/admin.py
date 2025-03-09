from django.contrib import admin
from .models import  PendingRecordModel, Case, CaseData

admin.site.register(PendingRecordModel)
admin.site.register(Case)
admin.site.register(CaseData)
