from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import ProducerProfile


class ProducerRegistrationTests(TestCase):
    valid_data = {
        "business_name": "Bristol Valley Farm",
        "contact_name": "Jane Smith",
        "email": "jane.smith@bristolvalleyfarm.com",
        "phone": "01179 123456",
        "business_address": "Bristol Valley Farm, Bristol",
        "postcode": "BS1 4DJ",
        "password1": "StrongProducerPass!2026",
        "password2": "StrongProducerPass!2026",
    }

    def test_tc001_registration_page_loads(self):
        response = self.client.get(reverse("producer_register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Producer Registration")
        self.assertContains(response, "business_name")
        self.assertContains(response, "contact_name")

    def test_tc001_valid_registration_creates_user_profile_role_and_hashed_password(self):
        response = self.client.post(reverse("producer_register"), self.valid_data)

        self.assertRedirects(response, reverse("producer_dashboard"))

        user = User.objects.get(email="jane.smith@bristolvalleyfarm.com")
        self.assertEqual(user.username, "jane.smith@bristolvalleyfarm.com")
        self.assertNotEqual(user.password, self.valid_data["password1"])
        self.assertTrue(user.check_password(self.valid_data["password1"]))

        profile = ProducerProfile.objects.get(user=user)
        self.assertEqual(profile.business_name, "Bristol Valley Farm")
        self.assertEqual(profile.contact_name, "Jane Smith")
        self.assertEqual(profile.phone, "01179 123456")
        self.assertEqual(profile.postcode, "BS1 4DJ")
        self.assertEqual(profile.role, ProducerProfile.ROLE_NAME)
        self.assertTrue(Group.objects.filter(name="Producer", user=user).exists())

    def test_tc001_registered_producer_can_login_and_view_profile(self):
        self.client.post(reverse("producer_register"), self.valid_data)
        self.client.logout()
        self.client.post(
            reverse("login"),
            {
                "username": self.valid_data["email"],
                "password": self.valid_data["password1"],
            },
        )

        response = self.client.get(reverse("producer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bristol Valley Farm")
        self.assertContains(response, "Jane Smith")
        self.assertContains(response, "producer")

    def test_tc001_duplicate_email_is_rejected(self):
        self.client.post(reverse("producer_register"), self.valid_data)

        response = self.client.post(reverse("producer_register"), self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
        self.assertEqual(User.objects.filter(email=self.valid_data["email"]).count(), 1)

    def test_tc001_weak_password_is_rejected(self):
        data = {
            **self.valid_data,
            "email": "weak-password@example.com",
            "password1": "123",
            "password2": "123",
        }

        response = self.client.post(reverse("producer_register"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This password is too short")
        self.assertFalse(User.objects.filter(email="weak-password@example.com").exists())
