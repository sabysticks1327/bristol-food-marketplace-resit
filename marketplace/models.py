from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

MONEY_QUANTIZER = Decimal("0.01")


def quantize_money(value):
    return Decimal(value).quantize(MONEY_QUANTIZER)


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


class Cart(models.Model):
    customer = models.OneToOneField(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cart for {self.customer}"

    @property
    def item_count(self):
        count = sum((item.quantity for item in self.items.all()), Decimal("0"))
        if count == count.to_integral_value():
            return int(count)
        return count

    @property
    def subtotal(self):
        return quantize_money(sum((item.line_total for item in self.items.all()), Decimal("0")))

    @property
    def producer_count(self):
        return self.items.values("product__producer").distinct().count()

    @property
    def single_producer(self):
        producers = {
            item.product.producer_id
            for item in self.items.select_related("product__producer")
        }
        if len(producers) != 1:
            return None
        return self.items.select_related("product__producer").first().product.producer


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_product_per_cart",
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def line_total(self):
        return quantize_money(self.product.price * self.quantity)


def generate_order_number():
    return f"BFM-{uuid4().hex[:10].upper()}"


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
    ]

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    producer = models.ForeignKey(
        ProducerProfile,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    order_number = models.CharField(
        max_length=24,
        unique=True,
        default=generate_order_number,
        editable=False,
    )
    delivery_address = models.TextField()
    delivery_postcode = models.CharField(max_length=12)
    delivery_date = models.DateField()
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    producer_payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def get_absolute_url(self):
        return reverse("order_detail", kwargs={"order_number": self.order_number})


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=150)
    product_category = models.CharField(max_length=80)
    unit = models.CharField(max_length=40)
    quantity = models.DecimalField(max_digits=9, decimal_places=2)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"


class PaymentRecord(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_CHOICES = [(STATUS_SUCCESS, "Success")]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment_record",
    )
    provider = models.CharField(max_length=80, default="test_sandbox")
    transaction_reference = models.CharField(max_length=80, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_SUCCESS,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.transaction_reference


class LoginAttempt(models.Model):
    email = models.EmailField()
    was_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        outcome = "successful" if self.was_successful else "failed"
        return f"{outcome} login for {self.email}"
