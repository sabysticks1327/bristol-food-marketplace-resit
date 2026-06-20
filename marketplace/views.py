from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .forms import ProducerRegistrationForm


def home(request):
    return render(request, "marketplace/home.html")


def require_producer(user):
    profile = getattr(user, "producer_profile", None)
    if profile is None:
        raise PermissionDenied("Only producer accounts can access this page.")
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
    return render(request, "marketplace/register.html", {"form": form})


@login_required
def producer_dashboard(request):
    producer = require_producer(request.user)
    return render(request, "marketplace/producer_dashboard.html", {"producer": producer})
