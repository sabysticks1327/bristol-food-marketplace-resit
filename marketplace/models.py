from django.conf import settings
from django.db import models


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
