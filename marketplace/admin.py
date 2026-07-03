from django.contrib import admin

from .models import CustomerProfile, ProducerProfile


admin.site.register(ProducerProfile)
admin.site.register(CustomerProfile)
