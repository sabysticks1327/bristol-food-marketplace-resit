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
    path("marketplace/", views.product_list, name="product_list"),
    path("marketplace/products/<int:pk>/", views.product_detail, name="product_detail"),
]
