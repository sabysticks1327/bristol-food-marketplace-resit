from datetime import timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone

from .models import CartItem, CustomerProfile, Order, ProducerProfile, Product


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


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
            "harvest_date",
        ]
        widgets = {
            "harvest_date": forms.DateInput(attrs={"type": "date"}),
        }


class AddToCartForm(forms.Form):
    quantity = forms.DecimalField(min_value=1, decimal_places=2, max_digits=8)

    def __init__(self, *args, product=None, **kwargs):
        self.product = product
        super().__init__(*args, **kwargs)

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if self.product and quantity > self.product.stock_quantity:
            raise forms.ValidationError("Requested quantity exceeds available stock.")
        return quantity


class CartQuantityForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ["quantity"]

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        if quantity > self.instance.product.stock_quantity:
            raise forms.ValidationError("Requested quantity exceeds available stock.")
        return quantity


class CheckoutForm(forms.Form):
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    delivery_postcode = forms.CharField(max_length=12)
    delivery_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    payment_method = forms.ChoiceField(
        choices=[("test_card", "Test card payment")],
        help_text="Use test/sandbox payment only.",
    )

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data["delivery_date"]
        minimum_date = timezone.localdate() + timedelta(days=2)
        if delivery_date < minimum_date:
            raise forms.ValidationError("Delivery date must allow at least 48 hours lead time.")
        return delivery_date


class OrderStatusForm(forms.ModelForm):
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = Order
        fields = ["status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = []
        for value, label in Order.STATUS_CHOICES:
            if self.instance.can_progress_to(value):
                allowed.append((value, label))
        self.fields["status"].choices = allowed

    def clean_status(self):
        status = self.cleaned_data["status"]
        if not self.instance.can_progress_to(status):
            raise forms.ValidationError("Order status must follow the required progression.")
        return status
