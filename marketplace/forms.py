from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.db import transaction

from .models import ProducerProfile


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


class ProducerRegistrationForm(UserCreationForm):
    business_name = forms.CharField(max_length=150)
    contact_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    business_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    postcode = forms.CharField(max_length=12)

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
