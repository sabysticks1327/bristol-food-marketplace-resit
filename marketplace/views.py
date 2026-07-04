from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomerRegistrationForm, ProducerRegistrationForm, ProductForm
from .models import Category, Product


def home(request):
    categories = Category.objects.all()
    products = visible_products().select_related("producer", "category")[:6]
    return render(
        request,
        "marketplace/home.html",
        {"categories": categories, "products": products},
    )


def visible_products():
    return Product.objects.filter(
        availability__in=[Product.AVAILABILITY_IN_SEASON, Product.AVAILABILITY_AVAILABLE],
        stock_quantity__gt=0,
    )


def require_producer(user):
    profile = getattr(user, "producer_profile", None)
    if profile is None:
        raise PermissionDenied("Only producer accounts can access this page.")
    return profile


def require_customer(user):
    profile = getattr(user, "customer_profile", None)
    if profile is None:
        raise PermissionDenied("Only customer accounts can access this page.")
    return profile


def producer_register(request):
    if request.method == "POST":
        form = ProducerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Producer account created successfully.")
            return redirect("producer_dashboard")
    else:
        form = ProducerRegistrationForm()
    return render(
        request,
        "marketplace/register.html",
        {"form": form, "account_type": "Producer"},
    )


def customer_register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Customer account created successfully.")
            return redirect("customer_account")
    else:
        form = CustomerRegistrationForm()
    return render(
        request,
        "marketplace/register.html",
        {"form": form, "account_type": "Customer"},
    )


@login_required
def producer_dashboard(request):
    producer = require_producer(request.user)
    products = producer.products.select_related("category")
    return render(
        request,
        "marketplace/producer_dashboard.html",
        {"producer": producer, "products": products},
    )


@login_required
def customer_account(request):
    customer = require_customer(request.user)
    return render(request, "marketplace/customer_account.html", {"customer": customer})


@login_required
def product_create(request):
    producer = require_producer(request.user)
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = producer
            product.save()
            messages.success(request, "Product listing created successfully.")
            return redirect("producer_dashboard")
    else:
        form = ProductForm()
    return render(request, "marketplace/product_form.html", {"form": form})


@login_required
def product_edit(request, pk):
    producer = require_producer(request.user)
    product = get_object_or_404(Product, pk=pk, producer=producer)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product listing updated successfully.")
            return redirect("producer_dashboard")
    else:
        form = ProductForm(instance=product)
    return render(request, "marketplace/product_form.html", {"form": form, "product": product})


def product_list(request):
    category_slug = request.GET.get("category")
    query = request.GET.get("q", "").strip()
    products = visible_products().select_related("producer", "category")
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(producer__business_name__icontains=query)
        )

    return render(
        request,
        "marketplace/product_list.html",
        {
            "categories": Category.objects.all(),
            "products": products,
            "query": query,
            "selected_category": selected_category,
        },
    )


def product_detail(request, pk):
    product = get_object_or_404(
        visible_products().select_related("producer", "category"),
        pk=pk,
    )
    return render(request, "marketplace/product_detail.html", {"product": product})
