from django.contrib import admin

from .models import (
    Cart,
    CartItem,
    Category,
    CustomerProfile,
    LoginAttempt,
    Order,
    OrderItem,
    PaymentRecord,
    ProducerProfile,
    Product,
)


admin.site.register(ProducerProfile)
admin.site.register(CustomerProfile)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PaymentRecord)
admin.site.register(LoginAttempt)
