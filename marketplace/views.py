from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AddToCartForm,
    CartQuantityForm,
    CheckoutForm,
    CustomerRegistrationForm,
    OrderStatusForm,
    ProducerRegistrationForm,
    ProductForm,
)
from .models import (
    CartItem,
    Category,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
)


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
    return render(request, "marketplace/register.html", {"form": form, "account_type": "Producer"})


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
    return render(request, "marketplace/register.html", {"form": form, "account_type": "Customer"})


@login_required
def customer_account(request):
    profile = require_customer(request.user)
    return render(request, "marketplace/customer_account.html", {"profile": profile})


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
    form = AddToCartForm(product=product, initial={"quantity": 1})
    return render(request, "marketplace/product_detail.html", {"product": product, "form": form})


@login_required
def cart_add(request, pk):
    require_customer(request.user)
    product = get_object_or_404(visible_products(), pk=pk)
    form = AddToCartForm(request.POST, product=product)
    if form.is_valid():
        item, created = CartItem.objects.get_or_create(
            customer=request.user,
            product=product,
            defaults={"quantity": form.cleaned_data["quantity"]},
        )
        if not created:
            item.quantity += form.cleaned_data["quantity"]
            item.save()
        messages.success(request, f"{product.name} added to cart.")
    else:
        messages.error(request, "Could not add product to cart.")
    return redirect("cart_detail")


@login_required
def cart_detail(request):
    require_customer(request.user)
    items = request.user.cart_items.select_related("product", "product__producer", "product__category")
    grouped_items = group_cart_items(items)
    total = sum((item.line_total for item in items), Decimal("0.00"))
    return render(
        request,
        "marketplace/cart.html",
        {"items": items, "grouped_items": grouped_items, "total": total},
    )


def group_cart_items(items):
    grouped = OrderedDict()
    for item in items:
        producer_name = item.product.producer.business_name
        grouped.setdefault(producer_name, {"producer": item.product.producer, "items": [], "subtotal": Decimal("0.00")})
        grouped[producer_name]["items"].append(item)
        grouped[producer_name]["subtotal"] += item.line_total
    return grouped


@login_required
def cart_update(request, pk):
    require_customer(request.user)
    item = get_object_or_404(CartItem, pk=pk, customer=request.user)
    form = CartQuantityForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, "Cart quantity updated.")
    else:
        messages.error(request, "Cart quantity could not be updated.")
    return redirect("cart_detail")


@login_required
def cart_remove(request, pk):
    require_customer(request.user)
    item = get_object_or_404(CartItem, pk=pk, customer=request.user)
    item.delete()
    messages.success(request, "Cart item removed.")
    return redirect("cart_detail")


@login_required
def checkout(request):
    profile = require_customer(request.user)
    items = list(request.user.cart_items.select_related("product", "product__producer"))
    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect("product_list")

    grouped_items = group_cart_items(items)
    total = sum((item.line_total for item in items), Decimal("0.00"))
    commission = (total * Decimal("0.05")).quantize(Decimal("0.01"))
    producer_total = (total * Decimal("0.95")).quantize(Decimal("0.01"))

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = create_order_from_cart(request.user, form.cleaned_data, items)
            messages.success(request, "Order placed successfully in test payment mode.")
            return redirect("order_confirmation", pk=order.pk)
    else:
        form = CheckoutForm(
            initial={
                "delivery_address": profile.delivery_address,
                "delivery_postcode": profile.postcode,
                "delivery_date": timezone.localdate() + timedelta(days=2),
            }
        )

    return render(
        request,
        "marketplace/checkout.html",
        {
            "form": form,
            "grouped_items": grouped_items,
            "total": total,
            "commission": commission,
            "producer_total": producer_total,
        },
    )


@transaction.atomic
def create_order_from_cart(user, data, cart_items):
    order = Order.objects.create(
        customer=user,
        order_number=f"BRFN-{timezone.now().strftime('%Y%m%d%H%M%S%f')}-{user.pk}",
        delivery_address=data["delivery_address"],
        delivery_postcode=data["delivery_postcode"].upper(),
        delivery_date=data["delivery_date"],
        special_instructions=data.get("special_instructions", ""),
    )
    for item in cart_items:
        product = item.product
        OrderItem.objects.create(
            order=order,
            product=product,
            producer=product.producer,
            product_name=product.name,
            unit_price=product.price,
            quantity=item.quantity,
        )
        product.stock_quantity -= item.quantity
        product.save(update_fields=["stock_quantity"])
        item.delete()
    order.recalculate_totals()
    OrderStatusHistory.objects.create(
        order=order,
        changed_by=order.customer,
        status=Order.STATUS_PENDING,
        note="Order created through test checkout.",
    )
    return order


@login_required
def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(
        request,
        "marketplace/order_confirmation.html",
        {"order": order, "producer_breakdown": order.producer_breakdown()},
    )


@login_required
def producer_orders(request):
    producer = require_producer(request.user)
    orders = (
        Order.objects.filter(items__producer=producer)
        .distinct()
        .prefetch_related("items", "status_history")
        .select_related("customer")
    )
    return render(request, "marketplace/producer_orders.html", {"producer": producer, "orders": orders})


@login_required
def producer_order_detail(request, pk):
    producer = require_producer(request.user)
    order = get_object_or_404(
        Order.objects.filter(items__producer=producer).distinct(),
        pk=pk,
    )
    producer_items = order.items.filter(producer=producer)
    return render(
        request,
        "marketplace/producer_order_detail.html",
        {"order": order, "producer": producer, "producer_items": producer_items},
    )


@login_required
def producer_order_status(request, pk):
    producer = require_producer(request.user)
    order = get_object_or_404(Order.objects.filter(items__producer=producer).distinct(), pk=pk)
    if request.method == "POST":
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            OrderStatusHistory.objects.create(
                order=order,
                changed_by=request.user,
                status=order.status,
                note=form.cleaned_data.get("note", ""),
            )
            messages.success(request, "Order status updated.")
            return redirect("producer_order_detail", pk=order.pk)
    else:
        form = OrderStatusForm(instance=order)
    return render(request, "marketplace/order_status_form.html", {"form": form, "order": order})

# Create your views here.
