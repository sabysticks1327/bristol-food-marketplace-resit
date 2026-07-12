import csv
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CartItemForm,
    CheckoutForm,
    CustomerRegistrationForm,
    OrderStatusUpdateForm,
    ProducerRegistrationForm,
    ProductForm,
)
from .models import (
    Cart,
    CartItem,
    Category,
    CustomerNotification,
    InventoryAlert,
    InventoryUpdate,
    LOW_STOCK_THRESHOLD,
    Order,
    OrderItem,
    OrderStatusHistory,
    PaymentRecord,
    ProducerProfile,
    Product,
    WeeklySettlement,
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


def decimal_text(value):
    return f"{value:.2f}"


def date_text(value):
    return value.isoformat() if value else None


def api_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def product_payload(product):
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category.name,
        "producer": product.producer.business_name,
        "description": product.description,
        "price": decimal_text(product.price),
        "unit": product.unit,
        "availability": product.availability_label,
        "stock_quantity": decimal_text(product.stock_quantity),
        "allergen_info": product.allergen_info,
        "organic_certified": product.organic_certified,
        "organic_label": product.organic_label,
        "certification_body": product.certification_body,
        "certification_number": product.certification_number,
        "harvest_date": date_text(product.harvest_date),
        "detail_url": product.get_absolute_url(),
    }


def order_item_payload(item):
    return {
        "product_name": item.product_name,
        "category": item.product_category,
        "quantity": decimal_text(item.quantity),
        "unit": item.unit,
        "unit_price": decimal_text(item.unit_price),
        "line_total": decimal_text(item.line_total),
    }


def order_payload(order):
    payment = getattr(order, "payment_record", None)
    return {
        "order_number": order.order_number,
        "producer": order.producer.business_name,
        "customer": f"Customer {order.customer_id}",
        "delivery_date": date_text(order.delivery_date),
        "status": order.get_status_display(),
        "subtotal": decimal_text(order.subtotal),
        "commission_amount": decimal_text(order.commission_amount),
        "producer_payment_amount": decimal_text(order.producer_payment_amount),
        "payment_reference": f"****{payment.transaction_reference[-4:]}" if payment else None,
        "items": [order_item_payload(item) for item in order.items.all()],
    }


def settlement_payload(settlement):
    return {
        "reference": settlement.reference,
        "producer": settlement.producer.business_name,
        "week_start": date_text(settlement.week_start),
        "week_end": date_text(settlement.week_end),
        "status": settlement.get_status_display(),
        "total_order_value": decimal_text(settlement.total_order_value),
        "commission_amount": decimal_text(settlement.commission_amount),
        "producer_payment_amount": decimal_text(settlement.producer_payment_amount),
        "orders": [order_payload(order) for order in settlement.orders.all()],
    }


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
    incoming_orders = (
        producer.orders.prefetch_related("items")
        .select_related("customer")
        .order_by("delivery_date", "created_at")
    )
    inventory_alerts = producer.inventory_alerts.filter(resolved=False).select_related("product")
    return render(
        request,
        "marketplace/producer_dashboard.html",
        {
            "producer": producer,
            "products": products,
            "incoming_orders": incoming_orders,
            "inventory_alerts": inventory_alerts,
        },
    )


@login_required
def customer_account(request):
    customer = require_customer(request.user)
    orders = customer.orders.prefetch_related("items").select_related("producer")
    notifications = customer.notifications.select_related("order")
    return render(
        request,
        "marketplace/customer_account.html",
        {"customer": customer, "orders": orders, "notifications": notifications},
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


def record_inventory_update(producer, product, previous_stock, previous_availability):
    if (
        product.stock_quantity == previous_stock
        and product.availability == previous_availability
    ):
        return

    InventoryUpdate.objects.create(
        product=product,
        producer=producer,
        previous_stock=previous_stock,
        new_stock=product.stock_quantity,
        previous_availability=previous_availability,
        new_availability=product.availability,
    )

    if (
        product.stock_quantity <= LOW_STOCK_THRESHOLD
        and product.availability in {
            Product.AVAILABILITY_IN_SEASON,
            Product.AVAILABILITY_AVAILABLE,
        }
    ):
        InventoryAlert.objects.get_or_create(
            product=product,
            producer=producer,
            resolved=False,
            defaults={
                "message": f"{product.name} stock is low: {product.stock_quantity} {product.unit} remaining."
            },
        )


@login_required
def product_edit(request, pk):
    producer = require_producer(request.user)
    product = get_object_or_404(Product, pk=pk, producer=producer)
    previous_stock = product.stock_quantity
    previous_availability = product.availability
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            record_inventory_update(
                producer,
                product,
                previous_stock,
                previous_availability,
            )
            messages.success(request, "Product listing updated successfully.")
            return redirect("producer_dashboard")
    else:
        form = ProductForm(instance=product)
    return render(request, "marketplace/product_form.html", {"form": form, "product": product})


def product_list(request):
    category_slug = request.GET.get("category")
    query = request.GET.get("q", "").strip()
    allergen_filter = request.GET.get("allergen", "").strip()
    organic_filter = request.GET.get("organic", "").strip()
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
            | Q(allergen_info__icontains=query)
        )

    if allergen_filter == "contains":
        products = products.exclude(allergen_info__iexact="No common allergens")
    elif allergen_filter == "none":
        products = products.filter(allergen_info__iexact="No common allergens")

    if organic_filter == "certified":
        products = products.filter(organic_certified=True)

    return render(
        request,
        "marketplace/product_list.html",
        {
            "categories": Category.objects.all(),
            "products": products,
            "query": query,
            "selected_category": selected_category,
            "allergen_filter": allergen_filter,
            "organic_filter": organic_filter,
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
            "add_to_cart_form": CartItemForm(
                product=product,
                initial={"quantity": 1},
                require_allergen_acknowledgement=True,
            ),
        },
    )


def api_root(request):
    return JsonResponse(
        {
            "service": "Bristol Food Marketplace API",
            "endpoints": {
                "categories": request.build_absolute_uri("/api/categories/"),
                "products": request.build_absolute_uri("/api/products/"),
                "customer_orders": request.build_absolute_uri("/api/customer/orders/"),
                "producer_orders": request.build_absolute_uri("/api/producer/orders/"),
                "producer_settlements": request.build_absolute_uri("/api/producer/settlements/"),
            },
        }
    )


def api_categories(request):
    categories = Category.objects.all()
    return JsonResponse(
        {
            "count": categories.count(),
            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "product_count": visible_products().filter(category=category).count(),
                }
                for category in categories
            ],
        }
    )


def api_products(request):
    category_slug = request.GET.get("category")
    query = request.GET.get("q", "").strip()
    allergen_filter = request.GET.get("allergen", "").strip()
    organic_filter = request.GET.get("organic", "").strip()
    products = visible_products().select_related("producer", "category")

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(producer__business_name__icontains=query)
            | Q(allergen_info__icontains=query)
        )
    if allergen_filter == "contains":
        products = products.exclude(allergen_info__iexact="No common allergens")
    elif allergen_filter == "none":
        products = products.filter(allergen_info__iexact="No common allergens")
    if organic_filter == "certified":
        products = products.filter(organic_certified=True)

    return JsonResponse(
        {
            "count": products.count(),
            "filters": {
                "category": category_slug,
                "q": query,
                "allergen": allergen_filter,
                "organic": organic_filter,
            },
            "products": [product_payload(product) for product in products],
        }
    )


def api_product_detail(request, pk):
    product = get_object_or_404(
        visible_products().select_related("producer", "category"),
        pk=pk,
    )
    return JsonResponse({"product": product_payload(product)})


def get_customer_cart(customer):
    cart, _ = Cart.objects.get_or_create(customer=customer)
    return cart


@login_required
@require_POST
def add_to_cart(request, pk):
    customer = require_customer(request.user)
    product = get_object_or_404(visible_products(), pk=pk)
    form = CartItemForm(
        request.POST,
        product=product,
        require_allergen_acknowledgement=True,
    )

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
                    special_instructions=form.cleaned_data["special_instructions"],
                    subtotal=subtotal,
                    commission_amount=commission,
                    producer_payment_amount=producer_payment,
                )
                OrderStatusHistory.objects.create(
                    order=order,
                    status=Order.STATUS_PENDING,
                    note="Order placed by customer.",
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

    status_form = None
    if producer is not None and order.producer_id == producer.id and order.allowed_next_status:
        status_form = OrderStatusUpdateForm(order=order)

    return render(
        request,
        "marketplace/order_detail.html",
        {"order": order, "status_form": status_form},
    )


def previous_completed_week(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    current_week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = current_week_start - timedelta(days=1)
    week_start = week_end - timedelta(days=6)
    return week_start, week_end


def parse_week_start(value):
    if not value:
        return previous_completed_week()[0]
    try:
        return date.fromisoformat(value)
    except ValueError:
        return previous_completed_week()[0]


def tax_year_start_for(end_date):
    start = date(end_date.year, 4, 6)
    if end_date < start:
        return date(end_date.year - 1, 4, 6)
    return start


def build_weekly_settlement(producer, week_start):
    week_end = week_start + timedelta(days=6)
    orders = (
        producer.orders.filter(
            status=Order.STATUS_DELIVERED,
            delivery_date__gte=week_start,
            delivery_date__lte=week_end,
        )
        .select_related("customer")
        .prefetch_related("items")
        .order_by("delivery_date", "created_at")
    )
    total_order_value = quantize_money(sum((order.subtotal for order in orders), Decimal("0")))
    commission_amount = quantize_money(sum((order.commission_amount for order in orders), Decimal("0")))
    producer_payment_amount = quantize_money(
        sum((order.producer_payment_amount for order in orders), Decimal("0"))
    )
    reference = f"SET-{producer.id}-{week_start:%Y%m%d}"
    settlement, _ = WeeklySettlement.objects.update_or_create(
        producer=producer,
        week_start=week_start,
        defaults={
            "week_end": week_end,
            "total_order_value": total_order_value,
            "commission_amount": commission_amount,
            "producer_payment_amount": producer_payment_amount,
            "reference": reference,
        },
    )
    settlement.orders.set(orders)
    return settlement, orders


@login_required
def producer_settlements(request):
    producer = require_producer(request.user)
    week_start = parse_week_start(request.GET.get("week_start"))
    settlement, orders = build_weekly_settlement(producer, week_start)
    tax_year_start = tax_year_start_for(settlement.week_end)
    tax_year_orders = producer.orders.filter(
        status=Order.STATUS_DELIVERED,
        delivery_date__gte=tax_year_start,
        delivery_date__lte=settlement.week_end,
    )
    tax_year_total = quantize_money(
        sum((order.producer_payment_amount for order in tax_year_orders), Decimal("0"))
    )
    historical_settlements = producer.weekly_settlements.order_by("-week_start")

    return render(
        request,
        "marketplace/producer_settlements.html",
        {
            "settlement": settlement,
            "orders": orders,
            "tax_year_start": tax_year_start,
            "tax_year_total": tax_year_total,
            "historical_settlements": historical_settlements,
        },
    )


@login_required
def settlement_report_csv(request, settlement_id):
    producer = require_producer(request.user)
    settlement = get_object_or_404(WeeklySettlement, pk=settlement_id, producer=producer)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="settlement-{settlement.reference}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(
        [
            "Settlement reference",
            settlement.reference,
            "Week",
            f"{settlement.week_start} to {settlement.week_end}",
            "Status",
            settlement.get_status_display(),
        ]
    )
    writer.writerow(
        [
            "Order number",
            "Customer",
            "Delivery date",
            "Items",
            "Order total",
            "Network commission",
            "Producer payment",
        ]
    )
    for order in settlement.orders.select_related("customer").prefetch_related("items"):
        items = "; ".join(
            f"{item.quantity} {item.unit} {item.product_name}"
            for item in order.items.all()
        )
        writer.writerow(
            [
                order.order_number,
                f"Customer {order.customer_id}",
                order.delivery_date,
                items,
                order.subtotal,
                order.commission_amount,
                order.producer_payment_amount,
            ]
        )
    writer.writerow([])
    writer.writerow(["Totals", "", "", "", settlement.total_order_value, settlement.commission_amount, settlement.producer_payment_amount])
    return response


@login_required
def order_history(request):
    customer = require_customer(request.user)
    orders = customer.orders.select_related("producer").prefetch_related("items").order_by("-created_at")
    producer_id = request.GET.get("producer")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if producer_id:
        orders = orders.filter(producer_id=producer_id)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    producers = ProducerProfile.objects.filter(orders__customer=customer).distinct()
    return render(
        request,
        "marketplace/order_history.html",
        {
            "orders": orders,
            "producers": producers,
            "producer_id": producer_id,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@login_required
@require_POST
def reorder(request, order_number):
    customer = require_customer(request.user)
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "items__product"),
        order_number=order_number,
        customer=customer,
    )
    cart = get_customer_cart(customer)
    added = 0
    skipped = []

    for item in order.items.all():
        product = item.product
        if product is None or not product.is_customer_visible:
            skipped.append(item.product_name)
            continue
        quantity = min(item.quantity, product.stock_quantity)
        if quantity <= 0:
            skipped.append(item.product_name)
            continue
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity = min(cart_item.quantity + quantity, product.stock_quantity)
            cart_item.save()
        added += 1

    if added:
        messages.success(request, f"{added} previous order item(s) added to your cart.")
    if skipped:
        messages.warning(
            request,
            "Unavailable products were skipped: " + ", ".join(skipped),
        )
    return redirect("cart_detail")


@login_required
def order_receipt_csv(request, order_number):
    customer = require_customer(request.user)
    order = get_object_or_404(
        Order.objects.select_related("producer", "payment_record").prefetch_related("items"),
        order_number=order_number,
        customer=customer,
    )
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="receipt-{order.order_number}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order", order.order_number])
    writer.writerow(["Producer", order.producer.business_name])
    writer.writerow(["Delivery date", order.delivery_date])
    writer.writerow(["Status", order.get_status_display()])
    writer.writerow(["Payment", f"{order.payment_record.provider} ****{order.payment_record.transaction_reference[-4:]}"])
    writer.writerow([])
    writer.writerow(["Product", "Quantity", "Unit price", "Line total"])
    for item in order.items.all():
        writer.writerow([item.product_name, f"{item.quantity} {item.unit}", item.unit_price, item.line_total])
    writer.writerow([])
    writer.writerow(["Total", order.subtotal])
    return response


@login_required
def api_customer_orders(request):
    customer = getattr(request.user, "customer_profile", None)
    if customer is None:
        return api_error("Customer account required.", status=403)

    orders = (
        customer.orders.select_related("producer", "payment_record")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return JsonResponse(
        {
            "count": orders.count(),
            "orders": [order_payload(order) for order in orders],
        }
    )


@login_required
def api_producer_orders(request):
    producer = getattr(request.user, "producer_profile", None)
    if producer is None:
        return api_error("Producer account required.", status=403)

    status = request.GET.get("status", "").strip()
    orders = (
        producer.orders.select_related("customer", "payment_record")
        .prefetch_related("items")
        .order_by("delivery_date", "created_at")
    )
    if status:
        orders = orders.filter(status=status)

    return JsonResponse(
        {
            "count": orders.count(),
            "filters": {"status": status},
            "orders": [order_payload(order) for order in orders],
        }
    )


@login_required
def api_producer_settlements(request):
    producer = getattr(request.user, "producer_profile", None)
    if producer is None:
        return api_error("Producer account required.", status=403)

    week_start = parse_week_start(request.GET.get("week_start"))
    settlement, _ = build_weekly_settlement(producer, week_start)
    settlement = (
        WeeklySettlement.objects.filter(pk=settlement.pk)
        .select_related("producer")
        .prefetch_related("orders", "orders__items")
        .get()
    )
    return JsonResponse({"settlement": settlement_payload(settlement)})


@login_required
def producer_orders(request):
    producer = require_producer(request.user)
    status = request.GET.get("status", "").strip()
    orders = (
        producer.orders.prefetch_related("items", "status_history")
        .select_related("customer")
        .order_by("delivery_date", "created_at")
    )
    if status:
        orders = orders.filter(status=status)

    return render(
        request,
        "marketplace/producer_orders.html",
        {
            "orders": orders,
            "status": status,
            "status_choices": Order.STATUS_CHOICES,
        },
    )


@login_required
@require_POST
def order_status_update(request, order_number):
    producer = require_producer(request.user)
    order = get_object_or_404(Order, order_number=order_number, producer=producer)
    form = OrderStatusUpdateForm(request.POST, order=order)

    if form.is_valid():
        new_status = form.cleaned_data["status"]
        note = form.cleaned_data["note"]
        order.status = new_status
        order.save(update_fields=["status"])
        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            note=note,
            updated_by=producer,
        )
        CustomerNotification.objects.create(
            customer=order.customer,
            order=order,
            message=(
                f"Order {order.order_number} status updated to "
                f"{order.get_status_display()}."
            ),
        )
        messages.success(request, "Order status updated.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect(order.get_absolute_url())
