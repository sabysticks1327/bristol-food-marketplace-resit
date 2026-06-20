from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailAuthenticationForm
from . import views

urlpatterns = [
    path("", views.home, name="marketplace_home"),
    path("accounts/producer/register/", views.producer_register, name="producer_register"),
    path("accounts/customer/register/", views.customer_register, name="customer_register"),
    path("accounts/customer/", views.customer_account, name="customer_account"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=EmailAuthenticationForm,
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("producer/dashboard/", views.producer_dashboard, name="producer_dashboard"),
    path("producer/products/new/", views.product_create, name="product_create"),
    path("producer/products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("producer/orders/", views.producer_orders, name="producer_orders"),
    path("producer/orders/<int:pk>/", views.producer_order_detail, name="producer_order_detail"),
    path("producer/orders/<int:pk>/status/", views.producer_order_status, name="producer_order_status"),
    path("marketplace/", views.product_list, name="product_list"),
    path("marketplace/products/<int:pk>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/<int:pk>/update/", views.cart_update, name="cart_update"),
    path("cart/<int:pk>/remove/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<int:pk>/confirmation/", views.order_confirmation, name="order_confirmation"),
]
