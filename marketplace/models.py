from django.conf import settings
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
