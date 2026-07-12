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
    CustomerNotification,
    InventoryAlert,
    InventoryUpdate,
    LoginAttempt,
    Order,
    OrderItem,
    OrderStatusHistory,
    PaymentRecord,
    ProducerProfile,
    Product,
    WeeklySettlement,
    quantize_money,
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
        organic_certified=False,
        certification_body="",
        certification_number="",
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
            organic_certified=organic_certified,
            certification_body=certification_body,
            certification_number=certification_number,
            harvest_date=date(2026, 7, 1),
        )

    def make_order(
        self,
        product,
        quantity="1.00",
        customer=None,
        delivery_date=None,
        status=Order.STATUS_PENDING,
        special_instructions="Leave with reception if needed.",
    ):
        quantity = Decimal(quantity)
        subtotal = quantize_money(product.price * quantity)
        order = Order.objects.create(
            customer=customer or self.customer,
            producer=product.producer,
            delivery_address=(customer or self.customer).delivery_address,
            delivery_postcode=(customer or self.customer).postcode,
            delivery_date=delivery_date or timezone.localdate() + timedelta(days=2),
            special_instructions=special_instructions,
            status=status,
            subtotal=subtotal,
            commission_amount=quantize_money(subtotal * Decimal("0.05")),
            producer_payment_amount=quantize_money(subtotal * Decimal("0.95")),
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            product_category=product.category.name,
            unit=product.unit,
            quantity=quantity,
            unit_price=product.price,
            line_total=subtotal,
        )
        PaymentRecord.objects.create(
            order=order,
            transaction_reference=f"TEST-{order.order_number}",
            amount=subtotal,
        )
        OrderStatusHistory.objects.create(
            order=order,
            status=status,
            note="Order created for test.",
        )
        return order

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
                {"quantity": "2.00", "allergen_acknowledged": "on"},
            ),
            carrots.get_absolute_url(),
        )
        self.assertRedirects(
            self.client.post(
                reverse("add_to_cart", kwargs={"pk": milk.pk}),
                {"quantity": "3.00", "allergen_acknowledged": "on"},
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
            {"quantity": "1.00", "allergen_acknowledged": "on"},
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
            {"quantity": "2.00", "allergen_acknowledged": "on"},
        )
        self.client.post(
            reverse("add_to_cart", kwargs={"pk": tomatoes.pk}),
            {"quantity": "1.00", "allergen_acknowledged": "on"},
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
            {"quantity": "1.00", "allergen_acknowledged": "on"},
        )
        self.client.post(
            reverse("add_to_cart", kwargs={"pk": milk.pk}),
            {"quantity": "1.00", "allergen_acknowledged": "on"},
        )

        response = self.client.get(reverse("checkout"))

        self.assertRedirects(response, reverse("cart_detail"))
        self.assertEqual(Order.objects.count(), 0)

    def test_tc009_producer_can_view_incoming_orders_sorted_by_delivery_date(self):
        carrots = self.make_product("Organic Carrots", self.vegetables)
        tomatoes = self.make_product("Organic Tomatoes", self.vegetables)
        milk = self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            price="1.80",
            unit="litre",
        )
        third_customer_user = User.objects.create_user(
            username="amelia.green@email.com",
            email="amelia.green@email.com",
            password="StrongCustomerPass!2026",
        )
        third_customer = CustomerProfile.objects.create(
            user=third_customer_user,
            full_name="Amelia Green",
            phone="07700 900777",
            delivery_address="12 Queen Square, Bristol",
            postcode="BS1 4NT",
            accepted_terms=True,
        )
        order_late = self.make_order(
            carrots,
            delivery_date=timezone.localdate() + timedelta(days=5),
        )
        order_early = self.make_order(
            tomatoes,
            delivery_date=timezone.localdate() + timedelta(days=2),
            special_instructions="Ring bell on arrival.",
        )
        order_middle = self.make_order(
            carrots,
            quantity="2.00",
            customer=third_customer,
            delivery_date=timezone.localdate() + timedelta(days=3),
        )
        other_producer_order = self.make_order(
            milk,
            delivery_date=timezone.localdate() + timedelta(days=2),
        )

        self.assertTrue(self.login_producer())
        response = self.client.get(reverse("producer_orders"))

        self.assertEqual(response.status_code, 200)
        orders = list(response.context["orders"])
        self.assertEqual(orders, [order_early, order_middle, order_late])
        self.assertContains(response, order_early.order_number)
        self.assertContains(response, "Robert Johnson")
        self.assertContains(response, "Amelia Green")
        self.assertContains(response, "Organic Tomatoes")
        self.assertContains(response, "2 days")
        self.assertNotContains(response, other_producer_order.order_number)

        detail = self.client.get(order_early.get_absolute_url())
        self.assertContains(detail, "07700 900123")
        self.assertContains(detail, "robert.johnson@email.com")
        self.assertContains(detail, "Ring bell on arrival.")
        self.assertContains(detail, "Lead time")

        filtered = self.client.get(
            reverse("producer_orders"),
            {"status": Order.STATUS_PENDING},
        )
        self.assertContains(filtered, order_early.order_number)

    def test_tc010_producer_updates_order_status_with_history_and_notification(self):
        carrots = self.make_product("Organic Carrots", self.vegetables)
        order = self.make_order(carrots)

        self.assertTrue(self.login_producer())
        response = self.client.post(
            reverse("order_status_update", kwargs={"order_number": order.order_number}),
            {
                "status": Order.STATUS_CONFIRMED,
                "note": "Products will be prepared by delivery date.",
            },
        )

        self.assertRedirects(response, order.get_absolute_url())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                status=Order.STATUS_CONFIRMED,
                note="Products will be prepared by delivery date.",
                updated_by=self.producer,
            ).exists()
        )
        self.assertTrue(
            CustomerNotification.objects.filter(
                customer=self.customer,
                order=order,
                message__icontains="Confirmed",
            ).exists()
        )

        invalid_skip = self.client.post(
            reverse("order_status_update", kwargs={"order_number": order.order_number}),
            {"status": Order.STATUS_DELIVERED, "note": "Skipping stages"},
        )
        self.assertRedirects(invalid_skip, order.get_absolute_url())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)

        ready_response = self.client.post(
            reverse("order_status_update", kwargs={"order_number": order.order_number}),
            {"status": Order.STATUS_READY, "note": "Ready for delivery."},
        )
        self.assertRedirects(ready_response, order.get_absolute_url())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_READY)

        self.client.logout()
        self.client.login(
            username="robert.johnson@email.com",
            password="StrongCustomerPass!2026",
        )
        account = self.client.get(reverse("customer_account"))
        self.assertContains(account, "Order")
        self.assertContains(account, "Ready for Delivery")

        self.client.logout()
        self.client.login(
            username="tom.harris@hillsidedairy.co.uk",
            password="StrongProducerPass!2026",
        )
        forbidden = self.client.post(
            reverse("order_status_update", kwargs={"order_number": order.order_number}),
            {"status": Order.STATUS_DELIVERED, "note": "Wrong producer"},
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_tc011_inventory_updates_save_history_alerts_and_public_visibility(self):
        tomatoes = self.make_product(
            "Organic Tomatoes",
            self.vegetables,
            stock_quantity="20.00",
            availability=Product.AVAILABILITY_AVAILABLE,
        )
        cabbage = self.make_product(
            "Winter Cabbage",
            self.vegetables,
            stock_quantity="8.00",
            availability=Product.AVAILABILITY_AVAILABLE,
        )
        self.assertTrue(self.login_producer())

        response = self.client.post(
            reverse("product_edit", kwargs={"pk": tomatoes.pk}),
            {
                "name": "Organic Tomatoes",
                "category": str(self.vegetables.pk),
                "description": tomatoes.description,
                "price": "2.50",
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": "35.00",
                "allergen_info": "No common allergens",
                "harvest_date": "2026-07-01",
            },
        )

        self.assertRedirects(response, reverse("producer_dashboard"))
        tomatoes.refresh_from_db()
        self.assertEqual(tomatoes.stock_quantity, Decimal("35.00"))
        self.assertEqual(tomatoes.availability, Product.AVAILABILITY_IN_SEASON)
        self.assertTrue(
            InventoryUpdate.objects.filter(
                product=tomatoes,
                previous_stock=Decimal("20.00"),
                new_stock=Decimal("35.00"),
            ).exists()
        )

        detail = self.client.get(tomatoes.get_absolute_url())
        self.assertContains(detail, "35.00 kg")

        self.client.post(
            reverse("product_edit", kwargs={"pk": cabbage.pk}),
            {
                "name": "Winter Cabbage",
                "category": str(self.vegetables.pk),
                "description": cabbage.description,
                "price": "2.50",
                "unit": "kg",
                "availability": Product.AVAILABILITY_UNAVAILABLE,
                "stock_quantity": "0.00",
                "allergen_info": "No common allergens",
                "harvest_date": "2026-07-01",
            },
        )
        hidden_response = self.client.get(reverse("product_list"), {"q": "Cabbage"})
        self.assertNotContains(hidden_response, "Winter Cabbage")

        self.client.post(
            reverse("product_edit", kwargs={"pk": tomatoes.pk}),
            {
                "name": "Organic Tomatoes",
                "category": str(self.vegetables.pk),
                "description": tomatoes.description,
                "price": "2.50",
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": "4.00",
                "allergen_info": "No common allergens",
                "harvest_date": "2026-07-01",
            },
        )
        self.assertTrue(
            InventoryAlert.objects.filter(
                product=tomatoes,
                message__icontains="stock is low",
                resolved=False,
            ).exists()
        )
        dashboard = self.client.get(reverse("producer_dashboard"))
        self.assertContains(dashboard, "stock is low")

        invalid_response = self.client.post(
            reverse("product_edit", kwargs={"pk": tomatoes.pk}),
            {
                "name": "Organic Tomatoes",
                "category": str(self.vegetables.pk),
                "description": tomatoes.description,
                "price": "2.50",
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": "-1.00",
                "allergen_info": "No common allergens",
                "harvest_date": "2026-07-01",
            },
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertContains(invalid_response, "Ensure this value is greater than or equal to 0.00")

    def test_tc012_weekly_settlement_includes_only_delivered_orders_and_csv_report(self):
        carrots = self.make_product("Organic Carrots", self.vegetables, price="2.00")
        tomatoes = self.make_product("Organic Tomatoes", self.vegetables, price="3.00")
        milk = self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            price="1.80",
            unit="litre",
        )
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday() + 7)
        delivered_one = self.make_order(
            carrots,
            quantity="3.00",
            delivery_date=week_start + timedelta(days=1),
            status=Order.STATUS_DELIVERED,
        )
        delivered_two = self.make_order(
            tomatoes,
            quantity="2.00",
            delivery_date=week_start + timedelta(days=3),
            status=Order.STATUS_DELIVERED,
        )
        pending_order = self.make_order(
            carrots,
            quantity="1.00",
            delivery_date=week_start + timedelta(days=4),
            status=Order.STATUS_PENDING,
        )
        other_producer_order = self.make_order(
            milk,
            quantity="5.00",
            delivery_date=week_start + timedelta(days=2),
            status=Order.STATUS_DELIVERED,
        )

        self.assertTrue(self.login_producer())
        response = self.client.get(
            reverse("producer_settlements"),
            {"week_start": week_start.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        settlement = response.context["settlement"]
        self.assertEqual(settlement.week_start, week_start)
        self.assertEqual(settlement.week_end, week_start + timedelta(days=6))
        self.assertEqual(settlement.total_order_value, Decimal("12.00"))
        self.assertEqual(settlement.commission_amount, Decimal("0.60"))
        self.assertEqual(settlement.producer_payment_amount, Decimal("11.40"))
        self.assertContains(response, "Pending Bank Transfer")
        self.assertContains(response, delivered_one.order_number)
        self.assertContains(response, delivered_two.order_number)
        self.assertNotContains(response, pending_order.order_number)
        self.assertNotContains(response, other_producer_order.order_number)
        self.assertTrue(
            WeeklySettlement.objects.filter(
                producer=self.producer,
                week_start=week_start,
                orders=delivered_one,
            ).exists()
        )

        csv_response = self.client.get(
            reverse("settlement_report_csv", kwargs={"settlement_id": settlement.pk})
        )
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response["Content-Type"], "text/csv")
        csv_body = csv_response.content.decode()
        self.assertIn(delivered_one.order_number, csv_body)
        self.assertIn("Network commission", csv_body)
        self.assertIn("11.40", csv_body)

        self.client.logout()
        self.client.login(
            username="tom.harris@hillsidedairy.co.uk",
            password="StrongProducerPass!2026",
        )
        forbidden = self.client.get(
            reverse("settlement_report_csv", kwargs={"settlement_id": settlement.pk})
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_tc014_organic_certification_filter_badges_and_producer_form(self):
        organic_carrots = self.make_product(
            "Organic Carrots",
            self.vegetables,
            organic_certified=True,
            certification_body="Soil Association",
            certification_number="SA-BVF-001",
        )
        self.make_product("Standard Carrots", self.vegetables)
        self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            organic_certified=True,
            certification_body="Organic Farmers & Growers",
            certification_number="OFG-HIL-010",
        )

        response = self.client.get(reverse("product_list"), {"organic": "certified"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organic Carrots")
        self.assertContains(response, "Fresh Milk")
        self.assertContains(response, "Certified Organic")
        self.assertNotContains(response, "Standard Carrots")

        category_response = self.client.get(
            reverse("product_list"),
            {"category": self.vegetables.slug, "organic": "certified"},
        )
        self.assertContains(category_response, "Organic Carrots")
        self.assertNotContains(category_response, "Fresh Milk")

        detail = self.client.get(organic_carrots.get_absolute_url())
        self.assertContains(detail, "Certified Organic - Soil Association")
        self.assertContains(detail, "SA-BVF-001")

        self.assertTrue(self.login_producer())
        missing_certification_body = self.client.post(
            reverse("product_create"),
            {
                "name": "Organic Mystery Box",
                "category": str(self.vegetables.pk),
                "description": "Certified box without body.",
                "price": "10.00",
                "unit": "box",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": "6.00",
                "allergen_info": "No common allergens",
                "organic_certified": "on",
                "certification_body": "",
                "certification_number": "CERT-001",
                "harvest_date": "2026-07-01",
            },
        )
        self.assertEqual(missing_certification_body.status_code, 200)
        self.assertContains(
            missing_certification_body,
            "Certification body is required for certified organic products.",
        )

    def test_tc021_customer_order_history_reorder_and_receipt(self):
        carrots = self.make_product(
            "Organic Carrots",
            self.vegetables,
            price="2.00",
            stock_quantity="20.00",
        )
        tomatoes = self.make_product(
            "Organic Tomatoes",
            self.vegetables,
            price="3.00",
            stock_quantity="10.00",
        )
        milk = self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            price="1.80",
            unit="litre",
            availability=Product.AVAILABILITY_UNAVAILABLE,
        )
        older_order = self.make_order(
            carrots,
            quantity="2.00",
            delivery_date=timezone.localdate() - timedelta(days=12),
            status=Order.STATUS_DELIVERED,
        )
        middle_order = self.make_order(
            tomatoes,
            quantity="1.00",
            delivery_date=timezone.localdate() - timedelta(days=8),
            status=Order.STATUS_DELIVERED,
        )
        newest_order = self.make_order(
            milk,
            quantity="3.00",
            delivery_date=timezone.localdate() - timedelta(days=5),
            status=Order.STATUS_DELIVERED,
        )

        self.assertTrue(self.login_customer())
        history = self.client.get(reverse("order_history"))

        self.assertEqual(history.status_code, 200)
        orders = list(history.context["orders"])
        self.assertEqual(orders, [newest_order, middle_order, older_order])
        self.assertContains(history, newest_order.order_number)
        self.assertContains(history, "Fresh Milk")
        self.assertContains(history, "Reorder")

        producer_filtered = self.client.get(
            reverse("order_history"),
            {"producer": self.producer.pk},
        )
        self.assertContains(producer_filtered, older_order.order_number)
        self.assertContains(producer_filtered, middle_order.order_number)
        self.assertNotContains(producer_filtered, newest_order.order_number)

        detail = self.client.get(middle_order.get_absolute_url())
        self.assertContains(detail, "****")
        self.assertContains(detail, "Download receipt")
        self.assertContains(detail, "Reorder")

        receipt = self.client.get(
            reverse("order_receipt_csv", kwargs={"order_number": middle_order.order_number})
        )
        self.assertEqual(receipt.status_code, 200)
        self.assertIn("Organic Tomatoes", receipt.content.decode())
        self.assertIn("****", receipt.content.decode())

        reorder_response = self.client.post(
            reverse("reorder", kwargs={"order_number": older_order.order_number})
        )
        self.assertRedirects(reorder_response, reverse("cart_detail"))
        cart = Cart.objects.get(customer=self.customer)
        self.assertTrue(cart.items.filter(product=carrots, quantity=Decimal("2.00")).exists())

        skipped_response = self.client.post(
            reverse("reorder", kwargs={"order_number": newest_order.order_number}),
            follow=True,
        )
        self.assertContains(skipped_response, "Unavailable products were skipped")
        self.assertFalse(cart.items.filter(product=milk).exists())

    def test_api_products_support_search_category_allergen_and_organic_filters(self):
        carrots = self.make_product(
            "Organic Carrots",
            self.vegetables,
            organic_certified=True,
            certification_body="Soil Association",
        )
        self.make_product(
            "Walnut Bread",
            self.vegetables,
            allergen_info="Wheat (Gluten), Nuts (Walnuts)",
        )
        self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            allergen_info="Milk",
        )

        root_response = self.client.get(reverse("api_root"))
        self.assertEqual(root_response.status_code, 200)
        self.assertIn("products", root_response.json()["endpoints"])

        response = self.client.get(
            reverse("api_products"),
            {"category": self.vegetables.slug, "organic": "certified"},
        )
        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["products"][0]["name"], "Organic Carrots")
        self.assertTrue(payload["products"][0]["organic_certified"])

        detail = self.client.get(reverse("api_product_detail", kwargs={"pk": carrots.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["product"]["certification_body"], "Soil Association")

        allergen_response = self.client.get(
            reverse("api_products"),
            {"allergen": "contains", "q": "walnut"},
        )
        self.assertEqual(allergen_response.json()["count"], 1)
        self.assertEqual(allergen_response.json()["products"][0]["name"], "Walnut Bread")

    def test_api_order_endpoints_are_role_protected_and_return_owned_data(self):
        carrots = self.make_product("Organic Carrots", self.vegetables, price="2.00")
        milk = self.make_product(
            "Fresh Milk",
            self.dairy,
            producer=self.hillside,
            price="1.80",
            unit="litre",
        )
        customer_order = self.make_order(
            carrots,
            quantity="2.00",
            delivery_date=timezone.localdate() + timedelta(days=2),
            status=Order.STATUS_CONFIRMED,
        )
        other_producer_order = self.make_order(
            milk,
            quantity="3.00",
            delivery_date=timezone.localdate() + timedelta(days=3),
            status=Order.STATUS_PENDING,
        )

        self.assertTrue(self.login_customer())
        customer_orders = self.client.get(reverse("api_customer_orders"))
        self.assertEqual(customer_orders.status_code, 200)
        order_numbers = [
            order["order_number"] for order in customer_orders.json()["orders"]
        ]
        self.assertIn(customer_order.order_number, order_numbers)
        self.assertIn(other_producer_order.order_number, order_numbers)
        self.assertTrue(customer_orders.json()["orders"][0]["payment_reference"].startswith("****"))

        forbidden_producer_api = self.client.get(reverse("api_producer_orders"))
        self.assertEqual(forbidden_producer_api.status_code, 403)

        self.client.logout()
        self.assertTrue(self.login_producer())
        producer_orders = self.client.get(reverse("api_producer_orders"))
        self.assertEqual(producer_orders.status_code, 200)
        producer_order_numbers = [
            order["order_number"] for order in producer_orders.json()["orders"]
        ]
        self.assertIn(customer_order.order_number, producer_order_numbers)
        self.assertNotIn(other_producer_order.order_number, producer_order_numbers)

        forbidden_customer_api = self.client.get(reverse("api_customer_orders"))
        self.assertEqual(forbidden_customer_api.status_code, 403)

    def test_api_producer_settlements_returns_weekly_commission_summary(self):
        carrots = self.make_product("Organic Carrots", self.vegetables, price="2.00")
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday() + 7)
        delivered_order = self.make_order(
            carrots,
            quantity="5.00",
            delivery_date=week_start + timedelta(days=1),
            status=Order.STATUS_DELIVERED,
        )
        self.make_order(
            carrots,
            quantity="1.00",
            delivery_date=week_start + timedelta(days=2),
            status=Order.STATUS_PENDING,
        )

        self.assertTrue(self.login_producer())
        response = self.client.get(
            reverse("api_producer_settlements"),
            {"week_start": week_start.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        settlement = response.json()["settlement"]
        self.assertEqual(settlement["total_order_value"], "10.00")
        self.assertEqual(settlement["commission_amount"], "0.50")
        self.assertEqual(settlement["producer_payment_amount"], "9.50")
        self.assertEqual(settlement["orders"][0]["order_number"], delivered_order.order_number)

        self.client.logout()
        self.assertTrue(self.login_customer())
        forbidden = self.client.get(reverse("api_producer_settlements"))
        self.assertEqual(forbidden.status_code, 403)

    def test_tc015_allergen_warnings_search_filters_and_acknowledgement(self):
        cheese = self.make_product(
            "Cheddar Cheese",
            self.dairy,
            description="Mature cheddar made with local dairy.",
            allergen_info="Milk",
        )
        bread = self.make_product(
            "Walnut Bread",
            self.vegetables,
            description="Fresh bakery loaf with walnuts.",
            allergen_info="Wheat (Gluten), Nuts (Walnuts)",
        )
        apples = self.make_product(
            "Fresh Apples",
            self.vegetables,
            description="Crisp orchard apples.",
            allergen_info="No common allergens",
        )

        cheese_detail = self.client.get(cheese.get_absolute_url())
        self.assertContains(cheese_detail, "Contains: Milk")
        self.assertContains(cheese_detail, "warning")

        bread_detail = self.client.get(bread.get_absolute_url())
        self.assertContains(bread_detail, "Contains: Wheat (Gluten), Nuts (Walnuts)")

        apple_detail = self.client.get(apples.get_absolute_url())
        self.assertContains(apple_detail, "No common allergens")

        nuts_search = self.client.get(reverse("product_list"), {"q": "nuts"})
        self.assertContains(nuts_search, "Walnut Bread")
        self.assertNotContains(nuts_search, "Cheddar Cheese")

        no_allergen_filter = self.client.get(reverse("product_list"), {"allergen": "none"})
        self.assertContains(no_allergen_filter, "Fresh Apples")
        self.assertNotContains(no_allergen_filter, "Walnut Bread")

        self.assertTrue(self.login_customer())
        blocked_cart = self.client.post(
            reverse("add_to_cart", kwargs={"pk": cheese.pk}),
            {"quantity": "1.00"},
        )
        self.assertRedirects(blocked_cart, cheese.get_absolute_url())
        self.assertFalse(Cart.objects.filter(customer=self.customer).exists())

        allowed_cart = self.client.post(
            reverse("add_to_cart", kwargs={"pk": cheese.pk}),
            {"quantity": "1.00", "allergen_acknowledged": "on"},
        )
        self.assertRedirects(allowed_cart, cheese.get_absolute_url())
        self.assertTrue(Cart.objects.filter(customer=self.customer).exists())

        self.client.logout()
        self.assertTrue(self.login_producer())
        missing_allergen = self.client.post(
            reverse("product_create"),
            {
                "name": "Mystery Jam",
                "category": str(self.vegetables.pk),
                "description": "Jam without allergen details.",
                "price": "4.00",
                "unit": "jar",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": "5.00",
                "allergen_info": "",
                "harvest_date": "2026-07-01",
            },
        )
        self.assertEqual(missing_allergen.status_code, 200)
        self.assertContains(missing_allergen, "Allergen information is required.")

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
