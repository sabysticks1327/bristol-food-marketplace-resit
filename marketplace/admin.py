from django.contrib import admin

from .models import (
    CartItem,
    Category,
    CustomerProfile,
    Order,
    OrderItem,
    OrderStatusHistory,
    ProducerProfile,
    Product,
)


admin.site.register(ProducerProfile)
admin.site.register(CustomerProfile)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderStatusHistory)
