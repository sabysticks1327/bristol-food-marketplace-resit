from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Cart,
    Category,
    CustomerProfile,
    LoginAttempt,
    Order,
    PaymentRecord,
    ProducerProfile,
    Product,
)


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
        self.customer = CustomerProfile.objects.create(
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

    def login_customer(self):
        return self.client.login(
            username="robert.johnson@email.com",
            password="StrongCustomerPass!2026",
        )

    def make_product(
        self,
        name,
        category,
        producer=None,
        description="Fresh local food from Bristol.",
        availability=Product.AVAILABILITY_IN_SEASON,
        stock_quantity="10.00",
        price="2.50",
        unit="kg",
        allergen_info="No common allergens",
    ):
        return Product.objects.create(
            producer=producer or self.producer,
            category=category,
            name=name,
            description=description,
            price=Decimal(price),
            unit=unit,
            availability=availability,
            stock_quantity=Decimal(stock_quantity),
            allergen_info=allergen_info,
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

    def test_tc006_customer_can_add_update_and_remove_cart_items(self):
        carrots = self.make_product(
            "Organic Carrots",
            self.vegetables,
            price="2.00",
            unit="kg",
            stock_quantity="50.00",
        )
        milk = self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            price="1.80",
            unit="litre",
            stock_quantity="35.00",
        )
        self.assertTrue(self.login_customer())

        self.assertRedirects(
            self.client.post(
                reverse("add_to_cart", kwargs={"pk": carrots.pk}),
                {"quantity": "2.00"},
            ),
            carrots.get_absolute_url(),
        )
        self.assertRedirects(
            self.client.post(
                reverse("add_to_cart", kwargs={"pk": milk.pk}),
                {"quantity": "3.00"},
            ),
            milk.get_absolute_url(),
        )

        cart = Cart.objects.get(customer=self.customer)
        self.assertEqual(cart.item_count, 5)
        self.assertEqual(cart.subtotal, Decimal("9.40"))

        response = self.client.get(reverse("cart_detail"))
        self.assertContains(response, "Cart (5)")
        self.assertContains(response, "Organic Carrots")
        self.assertContains(response, "Fresh Milk")
        self.assertContains(response, "Bristol Valley Farm")
        self.assertContains(response, "Hillside Dairy")
        self.assertContains(response, "9.40")

        carrot_item = cart.items.get(product=carrots)
        self.assertRedirects(
            self.client.post(
                reverse("cart_update_item", kwargs={"item_id": carrot_item.pk}),
                {"quantity": "3.00"},
            ),
            reverse("cart_detail"),
        )
        cart.refresh_from_db()
        self.assertEqual(cart.items.get(product=carrots).quantity, Decimal("3.00"))
        self.assertEqual(cart.subtotal, Decimal("11.40"))

        milk_item = cart.items.get(product=milk)
        self.assertRedirects(
            self.client.post(
                reverse("cart_remove_item", kwargs={"item_id": milk_item.pk})
            ),
            reverse("cart_detail"),
        )
        self.assertFalse(cart.items.filter(product=milk).exists())

    def test_tc006_only_customers_can_use_cart(self):
        carrots = self.make_product("Organic Carrots", self.vegetables)

        unauthenticated = self.client.post(
            reverse("add_to_cart", kwargs={"pk": carrots.pk}),
            {"quantity": "1.00"},
        )
        self.assertEqual(unauthenticated.status_code, 302)

        self.assertTrue(self.login_producer())
        producer_response = self.client.get(reverse("cart_detail"))
        self.assertEqual(producer_response.status_code, 403)

    def test_tc007_single_producer_checkout_creates_order_payment_and_clears_cart(self):
        carrots = self.make_product(
            "Organic Carrots",
            self.vegetables,
            price="2.00",
            unit="kg",
            stock_quantity="50.00",
        )
        tomatoes = self.make_product(
            "Organic Tomatoes",
            self.vegetables,
            price="3.00",
            unit="kg",
            stock_quantity="20.00",
        )
        self.assertTrue(self.login_customer())
        self.client.post(
            reverse("add_to_cart", kwargs={"pk": carrots.pk}),
            {"quantity": "2.00"},
        )
        self.client.post(
            reverse("add_to_cart", kwargs={"pk": tomatoes.pk}),
            {"quantity": "1.00"},
        )

        checkout_page = self.client.get(reverse("checkout"))
        self.assertEqual(checkout_page.status_code, 200)
        self.assertContains(checkout_page, "45 Park Street, Bristol")
        self.assertContains(checkout_page, "Bristol Valley Farm")
        self.assertContains(checkout_page, "Network commission (5%)")

        invalid_date = timezone.localdate() + timedelta(days=1)
        invalid_response = self.client.post(
            reverse("checkout"),
            {
                "delivery_address": "45 Park Street, Bristol",
                "delivery_postcode": "BS1 5JG",
                "delivery_date": invalid_date.isoformat(),
                "payment_method": "test_card",
            },
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertContains(invalid_response, "Delivery date must be at least 48 hours")
        self.assertEqual(Order.objects.count(), 0)

        delivery_date = timezone.localdate() + timedelta(days=2)
        response = self.client.post(
            reverse("checkout"),
            {
                "delivery_address": "45 Park Street, Bristol",
                "delivery_postcode": "BS1 5JG",
                "delivery_date": delivery_date.isoformat(),
                "payment_method": "test_card",
            },
        )

        order = Order.objects.get()
        self.assertRedirects(response, order.get_absolute_url())
        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.producer, self.producer)
        self.assertEqual(order.subtotal, Decimal("7.00"))
        self.assertEqual(order.commission_amount, Decimal("0.35"))
        self.assertEqual(order.producer_payment_amount, Decimal("6.65"))
        self.assertEqual(order.delivery_date, delivery_date)
        self.assertEqual(order.items.count(), 2)
        self.assertTrue(PaymentRecord.objects.filter(order=order, amount=Decimal("7.00")).exists())
        self.assertFalse(Cart.objects.get(customer=self.customer).items.exists())

        carrots.refresh_from_db()
        tomatoes.refresh_from_db()
        self.assertEqual(carrots.stock_quantity, Decimal("48.00"))
        self.assertEqual(tomatoes.stock_quantity, Decimal("19.00"))

        confirmation = self.client.get(order.get_absolute_url())
        self.assertContains(confirmation, order.order_number)
        self.assertContains(confirmation, "Producer payment (95%)")

        self.client.logout()
        self.client.login(
            username="jane.smith@bristolvalleyfarm.com",
            password="StrongProducerPass!2026",
        )
        producer_view = self.client.get(order.get_absolute_url())
        self.assertEqual(producer_view.status_code, 200)
        self.assertContains(producer_view, "Robert Johnson")

        self.client.logout()
        self.client.login(
            username="tom.harris@hillsidedairy.co.uk",
            password="StrongProducerPass!2026",
        )
        other_producer_view = self.client.get(order.get_absolute_url())
        self.assertEqual(other_producer_view.status_code, 403)

    def test_tc007_single_producer_checkout_blocks_mixed_producer_cart(self):
        carrots = self.make_product("Organic Carrots", self.vegetables)
        milk = self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            price="1.80",
            unit="litre",
        )
        self.assertTrue(self.login_customer())
        self.client.post(
            reverse("add_to_cart", kwargs={"pk": carrots.pk}),
            {"quantity": "1.00"},
        )
        self.client.post(
            reverse("add_to_cart", kwargs={"pk": milk.pk}),
            {"quantity": "1.00"},
        )

        response = self.client.get(reverse("checkout"))

        self.assertRedirects(response, reverse("cart_detail"))
        self.assertEqual(Order.objects.count(), 0)

    def test_tc022_login_security_logs_failures_and_rate_limits(self):
        login_url = reverse("login")
        for _ in range(5):
            response = self.client.post(
                login_url,
                {
                    "username": "robert.johnson@email.com",
                    "password": "WrongPassword!2026",
                },
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(
            LoginAttempt.objects.filter(
                email="robert.johnson@email.com",
                was_successful=False,
            ).count(),
            5,
        )

        blocked_response = self.client.post(
            login_url,
            {
                "username": "robert.johnson@email.com",
                "password": "StrongCustomerPass!2026",
            },
        )

        self.assertEqual(blocked_response.status_code, 200)
        self.assertContains(blocked_response, "Too many failed login attempts")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_tc022_password_hashing_logout_and_protected_pages(self):
        self.assertNotEqual(self.customer_user.password, "StrongCustomerPass!2026")
        self.assertTrue(self.customer_user.check_password("StrongCustomerPass!2026"))
        self.assertTrue(self.customer_user.password.startswith("pbkdf2_"))

        self.assertTrue(self.login_customer())
        account_response = self.client.get(reverse("customer_account"))
        self.assertEqual(account_response.status_code, 200)

        self.client.post(reverse("logout"))
        protected_response = self.client.get(reverse("customer_account"))
        self.assertEqual(protected_response.status_code, 302)
        self.assertIn(reverse("login"), protected_response["Location"])

    def test_tc022_authorisation_prevents_wrong_role_and_wrong_owner_access(self):
        carrots = self.make_product("Organic Carrots", self.vegetables)

        self.assertTrue(self.login_customer())
        customer_create_response = self.client.get(reverse("product_create"))
        self.assertEqual(customer_create_response.status_code, 403)

        self.client.logout()
        self.client.login(
            username="tom.harris@hillsidedairy.co.uk",
            password="StrongProducerPass!2026",
        )
        other_owner_response = self.client.get(
            reverse("product_edit", kwargs={"pk": carrots.pk})
        )
        self.assertEqual(other_owner_response.status_code, 404)

    def test_tc022_search_uses_orm_and_does_not_expose_unavailable_products(self):
        self.make_product("Organic Carrots", self.vegetables)
        self.make_product(
            "Hidden Cabbage",
            self.vegetables,
            availability=Product.AVAILABILITY_UNAVAILABLE,
        )

        response = self.client.get(reverse("product_list"), {"q": "' OR 1=1 --"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No products found")
        self.assertNotContains(response, "Hidden Cabbage")
