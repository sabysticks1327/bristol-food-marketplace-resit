from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CartItemForm,
    CheckoutForm,
    CustomerRegistrationForm,
    ProducerRegistrationForm,
    ProductForm,
)
from .models import (
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    PaymentRecord,
    Product,
    quantize_money,
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
    incoming_orders = producer.orders.prefetch_related("items").select_related("customer")
    return render(
        request,
        "marketplace/producer_dashboard.html",
        {
            "producer": producer,
            "products": products,
            "incoming_orders": incoming_orders,
        },
    )


@login_required
def customer_account(request):
    customer = require_customer(request.user)
    orders = customer.orders.prefetch_related("items").select_related("producer")
    return render(
        request,
        "marketplace/customer_account.html",
        {"customer": customer, "orders": orders},
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
    return render(
        request,
        "marketplace/product_detail.html",
        {
            "product": product,
            "add_to_cart_form": CartItemForm(product=product, initial={"quantity": 1}),
        },
    )


def get_customer_cart(customer):
    cart, _ = Cart.objects.get_or_create(customer=customer)
    return cart


@login_required
@require_POST
def add_to_cart(request, pk):
    customer = require_customer(request.user)
    product = get_object_or_404(visible_products(), pk=pk)
    form = CartItemForm(request.POST, product=product)

    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect(product.get_absolute_url())

    cart = get_customer_cart(customer)
    quantity = form.cleaned_data["quantity"]
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        item.quantity += quantity
        if item.quantity > product.stock_quantity:
            messages.error(
                request,
                f"Only {product.stock_quantity} {product.unit} available.",
            )
            return redirect(product.get_absolute_url())
        item.save()

    messages.success(request, f"{product.name} added to your cart.")
    return redirect(product.get_absolute_url())


@login_required
def cart_detail(request):
    customer = require_customer(request.user)
    cart = get_customer_cart(customer)
    items = cart.items.select_related("product", "product__producer", "product__category")
    return render(
        request,
        "marketplace/cart_detail.html",
        {"cart": cart, "items": items},
    )


@login_required
@require_POST
def cart_update_item(request, item_id):
    customer = require_customer(request.user)
    cart = get_customer_cart(customer)
    item = get_object_or_404(
        cart.items.select_related("product"),
        pk=item_id,
    )
    form = CartItemForm(request.POST, product=item.product)

    if form.is_valid():
        item.quantity = form.cleaned_data["quantity"]
        item.save()
        messages.success(request, "Cart quantity updated.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect("cart_detail")


@login_required
@require_POST
def cart_remove_item(request, item_id):
    customer = require_customer(request.user)
    cart = get_customer_cart(customer)
    item = get_object_or_404(cart.items.select_related("product"), pk=item_id)
    product_name = item.product.name
    item.delete()
    messages.success(request, f"{product_name} removed from your cart.")
    return redirect("cart_detail")


@login_required
def checkout(request):
    customer = require_customer(request.user)
    cart = get_customer_cart(customer)
    items = list(
        cart.items.select_related("product", "product__producer", "product__category")
    )

    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart_detail")

    producer = cart.single_producer
    if producer is None:
        messages.error(
            request,
            "Single-producer checkout requires all cart items to be from one producer.",
        )
        return redirect("cart_detail")

    initial = {
        "delivery_address": customer.delivery_address,
        "delivery_postcode": customer.postcode,
        "delivery_date": timezone.localdate() + timedelta(days=2),
        "payment_method": CheckoutForm.PAYMENT_TEST_CARD,
    }

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                cart = Cart.objects.select_for_update().get(pk=cart.pk)
                items = list(
                    cart.items.select_related(
                        "product",
                        "product__producer",
                        "product__category",
                    )
                )
                if not items:
                    messages.error(request, "Your cart is empty.")
                    return redirect("cart_detail")

                producer = cart.single_producer
                if producer is None:
                    messages.error(
                        request,
                        "Single-producer checkout requires all cart items to be from one producer.",
                    )
                    return redirect("cart_detail")

                for item in items:
                    if item.quantity > item.product.stock_quantity:
                        messages.error(
                            request,
                            f"{item.product.name} no longer has enough stock.",
                        )
                        return redirect("cart_detail")

                subtotal = cart.subtotal
                commission = quantize_money(subtotal * Decimal("0.05"))
                producer_payment = quantize_money(subtotal - commission)
                order = Order.objects.create(
                    customer=customer,
                    producer=producer,
                    delivery_address=form.cleaned_data["delivery_address"],
                    delivery_postcode=form.cleaned_data["delivery_postcode"].upper(),
                    delivery_date=form.cleaned_data["delivery_date"],
                    subtotal=subtotal,
                    commission_amount=commission,
                    producer_payment_amount=producer_payment,
                )

                for item in items:
                    product = item.product
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_category=product.category.name,
                        unit=product.unit,
                        quantity=item.quantity,
                        unit_price=product.price,
                        line_total=item.line_total,
                    )
                    product.stock_quantity -= item.quantity
                    product.save(update_fields=["stock_quantity", "updated_at"])

                PaymentRecord.objects.create(
                    order=order,
                    transaction_reference=f"TEST-{order.order_number}-{uuid4().hex[:6].upper()}",
                    amount=subtotal,
                )
                cart.items.all().delete()

            messages.success(
                request,
                f"Order {order.order_number} confirmed using test payment.",
            )
            return redirect(order.get_absolute_url())
    else:
        form = CheckoutForm(initial=initial)

    return render(
        request,
        "marketplace/checkout.html",
        {
            "cart": cart,
            "items": items,
            "form": form,
            "producer": producer,
            "minimum_delivery_date": initial["delivery_date"],
            "commission": quantize_money(cart.subtotal * Decimal("0.05")),
            "producer_payment": quantize_money(cart.subtotal * Decimal("0.95")),
        },
    )


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.select_related("customer", "producer").prefetch_related("items"),
        order_number=order_number,
    )
    customer = getattr(request.user, "customer_profile", None)
    producer = getattr(request.user, "producer_profile", None)

    if customer is not None and order.customer_id == customer.id:
        pass
    elif producer is not None and order.producer_id == producer.id:
        pass
    else:
        raise PermissionDenied("You do not have permission to view this order.")

    return render(request, "marketplace/order_detail.html", {"order": order})
