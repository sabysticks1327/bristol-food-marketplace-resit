from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CustomerProfile, LoginAttempt, Order, ProducerProfile, Product


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
    remember_me = forms.BooleanField(label="Remember me", required=False)

    max_recent_failures = 5

    def clean(self):
        email = self.cleaned_data.get("username", "").strip().lower()
        recent_cutoff = timezone.now() - timedelta(minutes=15)
        recent_failures = LoginAttempt.objects.filter(
            email__iexact=email,
            was_successful=False,
            created_at__gte=recent_cutoff,
        ).count()

        if email and recent_failures >= self.max_recent_failures:
            raise ValidationError(
                "Too many failed login attempts. Please wait before trying again.",
                code="too_many_login_attempts",
            )

        try:
            cleaned_data = super().clean()
        except ValidationError:
            if email:
                LoginAttempt.objects.create(email=email, was_successful=False)
            raise

        if email:
            LoginAttempt.objects.create(email=email, was_successful=True)
        return cleaned_data

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if self.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(60 * 60 * 24 * 14)
        else:
            self.request.session.set_expiry(0)


class BaseAccountCreationForm(UserCreationForm):
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    postcode = forms.CharField(max_length=12)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def create_user(self):
        email = self.cleaned_data["email"]
        user = super().save(commit=False)
        user.username = email
        user.email = email
        return user


class ProducerRegistrationForm(BaseAccountCreationForm):
    business_name = forms.CharField(max_length=150)
    contact_name = forms.CharField(max_length=150)
    business_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = User
        fields = [
            "business_name",
            "contact_name",
            "email",
            "phone",
            "business_address",
            "postcode",
            "password1",
            "password2",
        ]

    @transaction.atomic
    def save(self, commit=True):
        user = self.create_user()
        user.first_name = self.cleaned_data["contact_name"]
        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name="Producer")
            user.groups.add(group)
            ProducerProfile.objects.create(
                user=user,
                business_name=self.cleaned_data["business_name"],
                contact_name=self.cleaned_data["contact_name"],
                phone=self.cleaned_data["phone"],
                business_address=self.cleaned_data["business_address"],
                postcode=self.cleaned_data["postcode"].upper(),
            )
        return user


class CustomerRegistrationForm(BaseAccountCreationForm):
    full_name = forms.CharField(max_length=150)
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    accept_terms = forms.BooleanField(label="Accept terms and conditions")

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "phone",
            "delivery_address",
            "postcode",
            "accept_terms",
            "password1",
            "password2",
        ]

    @transaction.atomic
    def save(self, commit=True):
        user = self.create_user()
        user.first_name = self.cleaned_data["full_name"]
        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name="Customer")
            user.groups.add(group)
            CustomerProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"],
                phone=self.cleaned_data["phone"],
                delivery_address=self.cleaned_data["delivery_address"],
                postcode=self.cleaned_data["postcode"].upper(),
                accepted_terms=self.cleaned_data["accept_terms"],
            )
        return user


class ProductForm(forms.ModelForm):
    allergen_info = forms.CharField(
        max_length=255,
        help_text="Use standard language such as 'No common allergens' or 'Milk, Eggs, Nuts'.",
        error_messages={"required": "Allergen information is required."},
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "description",
            "price",
            "unit",
            "availability",
            "stock_quantity",
            "allergen_info",
            "organic_certified",
            "certification_body",
            "certification_number",
            "harvest_date",
        ]
        widgets = {
            "harvest_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_allergen_info(self):
        allergen_info = self.cleaned_data["allergen_info"].strip()
        if not allergen_info:
            raise forms.ValidationError("Allergen information is required.")
        return allergen_info

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("organic_certified") and not cleaned_data.get("certification_body"):
            self.add_error(
                "certification_body",
                "Certification body is required for certified organic products.",
            )
        return cleaned_data


class CartItemForm(forms.Form):
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=9,
        decimal_places=2,
        label="Quantity",
    )

    def __init__(self, *args, product=None, require_allergen_acknowledgement=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        if require_allergen_acknowledgement:
            self.fields["allergen_acknowledged"] = forms.BooleanField(
                label="I have reviewed the allergen information for this product.",
                required=True,
            )

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if self.product and quantity > self.product.stock_quantity:
            raise forms.ValidationError(
                f"Only {self.product.stock_quantity} {self.product.unit} available."
            )
        return quantity


class CheckoutForm(forms.Form):
    PAYMENT_TEST_CARD = "test_card"
    PAYMENT_CHOICES = [(PAYMENT_TEST_CARD, "Test sandbox card")]

    delivery_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    delivery_postcode = forms.CharField(max_length=12)
    delivery_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data["delivery_date"]
        minimum_date = timezone.localdate() + timedelta(days=2)
        if delivery_date < minimum_date:
            raise forms.ValidationError(
                "Delivery date must be at least 48 hours from today."
            )
        return delivery_date


class OrderStatusUpdateForm(forms.Form):
    status = forms.ChoiceField(choices=Order.STATUS_CHOICES)
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order
        next_status = order.allowed_next_status if order else None
        if next_status:
            self.fields["status"].choices = [
                (next_status, dict(Order.STATUS_CHOICES)[next_status])
            ]
        else:
            self.fields["status"].choices = []
            self.fields["status"].disabled = True

    def clean_status(self):
        status = self.cleaned_data["status"]
        if self.order and not self.order.can_transition_to(status):
            raise forms.ValidationError("Order status must follow the required progression.")
        return status
