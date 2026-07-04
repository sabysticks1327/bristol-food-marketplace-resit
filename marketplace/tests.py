from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Category, CustomerProfile, ProducerProfile, Product


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


class CustomerRegistrationTests(TestCase):
    valid_data = {
        "full_name": "Robert Johnson",
        "email": "robert.johnson@email.com",
        "phone": "07700 900123",
        "delivery_address": "45 Park Street, Bristol",
        "postcode": "BS1 5JG",
        "accept_terms": "on",
        "password1": "StrongCustomerPass!2026",
        "password2": "StrongCustomerPass!2026",
    }

    def test_tc002_registration_page_loads(self):
        response = self.client.get(reverse("customer_register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Customer Registration")
        self.assertContains(response, "full_name")
        self.assertContains(response, "delivery_address")

    def test_tc002_valid_registration_creates_customer_profile_role_and_hashed_password(self):
        response = self.client.post(reverse("customer_register"), self.valid_data)

        self.assertRedirects(response, reverse("customer_account"))

        user = User.objects.get(email="robert.johnson@email.com")
        self.assertEqual(user.username, "robert.johnson@email.com")
        self.assertNotEqual(user.password, self.valid_data["password1"])
        self.assertTrue(user.check_password(self.valid_data["password1"]))

        profile = CustomerProfile.objects.get(user=user)
        self.assertEqual(profile.full_name, "Robert Johnson")
        self.assertEqual(profile.phone, "07700 900123")
        self.assertEqual(profile.delivery_address, "45 Park Street, Bristol")
        self.assertEqual(profile.postcode, "BS1 5JG")
        self.assertEqual(profile.role, CustomerProfile.ROLE_NAME)
        self.assertTrue(profile.accepted_terms)
        self.assertTrue(Group.objects.filter(name="Customer", user=user).exists())

    def test_tc002_registered_customer_can_login_and_view_account(self):
        self.client.post(reverse("customer_register"), self.valid_data)
        self.client.logout()
        self.client.post(
            reverse("login"),
            {
                "username": self.valid_data["email"],
                "password": self.valid_data["password1"],
            },
        )

        response = self.client.get(reverse("customer_account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Robert Johnson")
        self.assertContains(response, "45 Park Street, Bristol")
        self.assertContains(response, "customer")

    def test_tc002_terms_must_be_accepted(self):
        data = {**self.valid_data}
        data.pop("accept_terms")

        response = self.client.post(reverse("customer_register"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertFalse(User.objects.filter(email=self.valid_data["email"]).exists())

    def test_tc002_customer_cannot_access_producer_profile_page(self):
        self.client.post(reverse("customer_register"), self.valid_data)

        response = self.client.get(reverse("producer_dashboard"))

        self.assertEqual(response.status_code, 403)


class ProductMarketplaceTests(TestCase):
    def setUp(self):
        producer_group, _ = Group.objects.get_or_create(name="Producer")
        customer_group, _ = Group.objects.get_or_create(name="Customer")

        self.producer_user = User.objects.create_user(
            username="jane.smith@bristolvalleyfarm.com",
            email="jane.smith@bristolvalleyfarm.com",
            password="StrongProducerPass!2026",
        )
        self.producer_user.groups.add(producer_group)
        self.producer = ProducerProfile.objects.create(
            user=self.producer_user,
            business_name="Bristol Valley Farm",
            contact_name="Jane Smith",
            phone="01179 123456",
            business_address="Bristol Valley Farm, Bristol",
            postcode="BS1 4DJ",
        )

        self.hillside_user = User.objects.create_user(
            username="tom.harris@hillsidedairy.co.uk",
            email="tom.harris@hillsidedairy.co.uk",
            password="StrongProducerPass!2026",
        )
        self.hillside_user.groups.add(producer_group)
        self.hillside = ProducerProfile.objects.create(
            user=self.hillside_user,
            business_name="Hillside Dairy",
            contact_name="Tom Harris",
            phone="01179 654321",
            business_address="Hillside Dairy, North Somerset",
            postcode="BS40 5AA",
        )

        self.customer_user = User.objects.create_user(
            username="robert.johnson@email.com",
            email="robert.johnson@email.com",
            password="StrongCustomerPass!2026",
        )
        self.customer_user.groups.add(customer_group)
        CustomerProfile.objects.create(
            user=self.customer_user,
            full_name="Robert Johnson",
            phone="07700 900123",
            delivery_address="45 Park Street, Bristol",
            postcode="BS1 5JG",
            accepted_terms=True,
        )

        self.vegetables = Category.objects.create(name="Vegetables", slug="vegetables")
        self.dairy = Category.objects.create(name="Dairy Products", slug="dairy-products")

    def login_producer(self):
        return self.client.login(
            username="jane.smith@bristolvalleyfarm.com",
            password="StrongProducerPass!2026",
        )

    def make_product(
        self,
        name,
        category,
        producer=None,
        description="Fresh local food from Bristol.",
        availability=Product.AVAILABILITY_IN_SEASON,
        stock_quantity="10.00",
    ):
        return Product.objects.create(
            producer=producer or self.producer,
            category=category,
            name=name,
            description=description,
            price=Decimal("2.50"),
            unit="kg",
            availability=availability,
            stock_quantity=Decimal(stock_quantity),
            allergen_info="No common allergens",
            harvest_date=date(2026, 7, 1),
        )

    def test_tc003_authenticated_producer_can_create_product_listing(self):
        self.assertTrue(self.login_producer())

        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Organic Carrots",
                "category": str(self.vegetables.pk),
                "description": "Fresh organic carrots grown near Bristol.",
                "price": "2.00",
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": "50.00",
                "allergen_info": "No common allergens",
                "harvest_date": "2026-07-01",
            },
        )

        self.assertRedirects(response, reverse("producer_dashboard"))
        product = Product.objects.get(name="Organic Carrots")
        self.assertEqual(product.producer, self.producer)
        self.assertEqual(product.category, self.vegetables)
        self.assertEqual(product.price, Decimal("2.00"))
        self.assertTrue(product.is_customer_visible)

        dashboard = self.client.get(reverse("producer_dashboard"))
        self.assertContains(dashboard, "Organic Carrots")
        self.assertContains(dashboard, "Vegetables")
        self.assertContains(dashboard, "Edit")

        public_detail = self.client.get(reverse("product_detail", kwargs={"pk": product.pk}))
        self.assertContains(public_detail, "Organic Carrots")
        self.assertContains(public_detail, "Fresh organic carrots")

    def test_tc003_customer_cannot_create_product_listing(self):
        self.client.login(
            username="robert.johnson@email.com",
            password="StrongCustomerPass!2026",
        )

        response = self.client.get(reverse("product_create"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.count(), 0)

    def test_tc004_customers_can_browse_products_by_category(self):
        self.make_product("Organic Carrots", self.vegetables)
        self.make_product("Organic Tomatoes", self.vegetables)
        self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            description="Whole milk from Hillside Dairy.",
        )
        self.make_product(
            "Hidden Cabbage",
            self.vegetables,
            availability=Product.AVAILABILITY_UNAVAILABLE,
        )

        response = self.client.get(
            reverse("product_list"),
            {"category": self.vegetables.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organic Carrots")
        self.assertContains(response, "Organic Tomatoes")
        self.assertNotContains(response, "Fresh Milk")
        self.assertNotContains(response, "Hidden Cabbage")
        self.assertContains(response, "Vegetables")

    def test_tc005_search_matches_product_description_and_producer(self):
        self.make_product("Organic Carrots", self.vegetables)
        self.make_product(
            "Organic Tomatoes",
            self.vegetables,
            description="Sweet seasonal tomatoes for salads and sauces.",
        )
        self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            description="Whole milk from Hillside Dairy.",
        )

        name_response = self.client.get(reverse("product_list"), {"q": "tomatoes"})
        self.assertContains(name_response, "Organic Tomatoes")
        self.assertNotContains(name_response, "Fresh Milk")

        description_response = self.client.get(reverse("product_list"), {"q": "seasonal"})
        self.assertContains(description_response, "Organic Tomatoes")

        producer_response = self.client.get(reverse("product_list"), {"q": "Hillside"})
        self.assertContains(producer_response, "Fresh Milk")
        self.assertNotContains(producer_response, "Organic Carrots")

    def test_tc005_search_no_results_message_is_shown(self):
        self.make_product("Organic Carrots", self.vegetables)

        response = self.client.get(reverse("product_list"), {"q": "dragonfruit"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No products found")
        self.assertNotContains(response, "Organic Carrots")
