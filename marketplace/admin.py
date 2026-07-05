from django.contrib import admin

from .models import (
    Cart,
    CartItem,
    Category,
    CustomerProfile,
    CustomerNotification,
    InventoryAlert,
    InventoryUpdate,
    LoginAttempt,
    Order,
    OrderItem,
    OrderStatusHistory,
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
admin.site.register(OrderStatusHistory)
admin.site.register(CustomerNotification)
admin.site.register(InventoryUpdate)
admin.site.register(InventoryAlert)
