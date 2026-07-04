from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.db import transaction

from .models import CustomerProfile, ProducerProfile, Product


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
