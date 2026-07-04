from django.contrib import admin

from .models import Category, CustomerProfile, ProducerProfile, Product


admin.site.register(ProducerProfile)
admin.site.register(CustomerProfile)
admin.site.register(Category)
admin.site.register(Product)
