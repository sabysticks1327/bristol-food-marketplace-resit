from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class ProducerProfile(models.Model):
    ROLE_NAME = "producer"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="producer_profile",
    )
    business_name = models.CharField(max_length=150)
    contact_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    business_address = models.TextField()
    postcode = models.CharField(max_length=12)
    role = models.CharField(max_length=30, default=ROLE_NAME, editable=False)
    verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["business_name"]

    def __str__(self):
        return self.business_name


class CustomerProfile(models.Model):
    ROLE_NAME = "customer"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    delivery_address = models.TextField()
    postcode = models.CharField(max_length=12)
    role = models.CharField(max_length=30, default=ROLE_NAME, editable=False)
    accepted_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    AVAILABILITY_IN_SEASON = "in_season"
    AVAILABILITY_AVAILABLE = "available"
    AVAILABILITY_UNAVAILABLE = "unavailable"
    AVAILABILITY_OUT_OF_SEASON = "out_of_season"
    AVAILABILITY_CHOICES = [
        (AVAILABILITY_IN_SEASON, "In Season"),
        (AVAILABILITY_AVAILABLE, "Available"),
        (AVAILABILITY_UNAVAILABLE, "Unavailable"),
        (AVAILABILITY_OUT_OF_SEASON, "Out of Season"),
    ]

    producer = models.ForeignKey(
        ProducerProfile,
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=150)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    unit = models.CharField(max_length=40)
    availability = models.CharField(
        max_length=30,
        choices=AVAILABILITY_CHOICES,
        default=AVAILABILITY_IN_SEASON,
    )
    stock_quantity = models.DecimalField(max_digits=9, decimal_places=2)
    allergen_info = models.CharField(max_length=255, blank=True)
    harvest_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"pk": self.pk})

    @property
    def is_customer_visible(self):
        return self.availability in {
            self.AVAILABILITY_IN_SEASON,
            self.AVAILABILITY_AVAILABLE,
        } and self.stock_quantity > 0

    @property
    def availability_label(self):
        return dict(self.AVAILABILITY_CHOICES).get(self.availability, self.availability)


class CartItem(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer", "product")
        ordering = ["product__producer__business_name", "product__name"]

    def __str__(self):
        return f"{self.product} x {self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.product.price


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_READY = "ready"
    STATUS_DELIVERED = "delivered"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_READY, "Ready"),
        (STATUS_DELIVERED, "Delivered"),
    ]
    STATUS_PROGRESS = [STATUS_PENDING, STATUS_CONFIRMED, STATUS_READY, STATUS_DELIVERED]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    delivery_address = models.TextField()
    delivery_postcode = models.CharField(max_length=12)
    delivery_date = models.DateField()
    special_instructions = models.TextField(blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    producer_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["delivery_date", "created_at"]

    def __str__(self):
        return self.order_number

    def recalculate_totals(self):
        total = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
        self.total = total
        self.commission = (total * Decimal("0.05")).quantize(Decimal("0.01"))
        self.producer_total = (total * Decimal("0.95")).quantize(Decimal("0.01"))
        self.save(update_fields=["total", "commission", "producer_total"])

    def producer_breakdown(self):
        breakdown = {}
        for item in self.items.select_related("producer", "product"):
            name = item.producer.business_name
            breakdown.setdefault(
                name,
                {
                    "producer": item.producer,
                    "items": [],
                    "subtotal": Decimal("0.00"),
                    "producer_payment": Decimal("0.00"),
                },
            )
            breakdown[name]["items"].append(item)
            breakdown[name]["subtotal"] += item.line_total

        for entry in breakdown.values():
            entry["producer_payment"] = (
                entry["subtotal"] * Decimal("0.95")
            ).quantize(Decimal("0.01"))

        return breakdown

    def can_progress_to(self, next_status):
        try:
            current_index = self.STATUS_PROGRESS.index(self.status)
            next_index = self.STATUS_PROGRESS.index(next_status)
        except ValueError:
            return False
        return next_index == current_index + 1


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    producer = models.ForeignKey(ProducerProfile, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["producer__business_name", "product_name"]

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def clean(self):
        if self.changed_by_id and not hasattr(self.changed_by, "producer_profile"):
            raise ValidationError("Only producer users can update order status.")
