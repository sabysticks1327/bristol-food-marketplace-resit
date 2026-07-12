from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import EmailAuthenticationForm
from . import views

urlpatterns = [
    path("", views.home, name="marketplace_home"),
    path("api/", views.api_root, name="api_root"),
    path("api/categories/", views.api_categories, name="api_categories"),
    path("api/products/", views.api_products, name="api_products"),
    path("api/products/<int:pk>/", views.api_product_detail, name="api_product_detail"),
    path("api/customer/orders/", views.api_customer_orders, name="api_customer_orders"),
    path("api/producer/orders/", views.api_producer_orders, name="api_producer_orders"),
    path(
        "api/producer/settlements/",
        views.api_producer_settlements,
        name="api_producer_settlements",
    ),
    path("accounts/producer/register/", views.producer_register, name="producer_register"),
    path("accounts/customer/register/", views.customer_register, name="customer_register"),
    path("accounts/customer/", views.customer_account, name="customer_account"),
    path("accounts/customer/orders/", views.order_history, name="order_history"),
    path("accounts/customer/orders/<str:order_number>/reorder/", views.reorder, name="reorder"),
    path("accounts/customer/orders/<str:order_number>/receipt.csv", views.order_receipt_csv, name="order_receipt_csv"),
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
    path("marketplace/", views.product_list, name="product_list"),
    path("marketplace/products/<int:pk>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/items/<int:item_id>/update/", views.cart_update_item, name="cart_update_item"),
    path("cart/items/<int:item_id>/remove/", views.cart_remove_item, name="cart_remove_item"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
    path("producer/orders/", views.producer_orders, name="producer_orders"),
    path("producer/payments/", views.producer_settlements, name="producer_settlements"),
    path(
        "producer/payments/<int:settlement_id>/report.csv",
        views.settlement_report_csv,
        name="settlement_report_csv",
    ),
    path(
        "producer/orders/<str:order_number>/status/",
        views.order_status_update,
        name="order_status_update",
    ),
]
