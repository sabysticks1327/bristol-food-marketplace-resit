from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    CartItem,
    Category,
    CustomerProfile,
    Order,
    OrderItem,
    OrderStatusHistory,
    ProducerProfile,
    Product,
)


class MarketplaceCaseTests(TestCase):
    def setUp(self):
        self.vegetables = Category.objects.create(name="Vegetables", slug="vegetables")
        self.dairy = Category.objects.create(name="Dairy Products", slug="dairy-products")
        self.eggs_category = Category.objects.create(name="Dairy & Eggs", slug="dairy-eggs")

        self.producer_user = self.create_producer(
            email="producer@example.com",
            business_name="Bristol Valley Farm",
            contact_name="Jane Smith",
        )
        self.second_producer_user = self.create_producer(
            email="hillside@example.com",
            business_name="Hillside Dairy",
            contact_name="Aisha Patel",
        )
        self.customer_user = self.create_customer()

        self.carrots = Product.objects.create(
            producer=self.producer_user.producer_profile,
            category=self.vegetables,
            name="Organic Carrots",
            description="Fresh organic carrots grown near Bristol.",
            price=Decimal("2.00"),
            unit="kg",
            availability=Product.AVAILABILITY_IN_SEASON,
            stock_quantity=Decimal("50.00"),
            allergen_info="No common allergens",
            harvest_date=date.today(),
        )
        self.tomatoes = Product.objects.create(
            producer=self.producer_user.producer_profile,
            category=self.vegetables,
            name="Organic Tomatoes",
            description="Organic tomatoes with rich flavour.",
            price=Decimal("3.00"),
            unit="kg",
            availability=Product.AVAILABILITY_IN_SEASON,
            stock_quantity=Decimal("20.00"),
        )
        self.milk = Product.objects.create(
            producer=self.second_producer_user.producer_profile,
            category=self.dairy,
            name="Fresh Milk",
            description="Fresh local milk from Hillside Dairy.",
            price=Decimal("1.80"),
            unit="litre",
            availability=Product.AVAILABILITY_AVAILABLE,
            stock_quantity=Decimal("80.00"),
            allergen_info="Contains: Milk",
        )

    def create_producer(self, email, business_name, contact_name):
        user = User.objects.create_user(
            username=email,
            email=email,
            password="StrongProducerPass!2026",
            first_name=contact_name,
        )
        group, _ = Group.objects.get_or_create(name="Producer")
        user.groups.add(group)
        ProducerProfile.objects.create(
            user=user,
            business_name=business_name,
            contact_name=contact_name,
            phone="01179 123456",
            business_address=f"{business_name}, Bristol",
            postcode="BS1 4DJ",
        )
        return user

    def create_customer(self):
        user = User.objects.create_user(
            username="robert.johnson@email.com",
            email="robert.johnson@email.com",
            password="StrongCustomerPass!2026",
            first_name="Robert Johnson",
        )
        group, _ = Group.objects.get_or_create(name="Customer")
        user.groups.add(group)
        CustomerProfile.objects.create(
            user=user,
            full_name="Robert Johnson",
            phone="07700 900123",
            delivery_address="45 Park Street, Bristol",
            postcode="BS1 5JG",
            accepted_terms=True,
        )
        return user

    def login_customer(self):
        self.client.login(username=self.customer_user.email, password="StrongCustomerPass!2026")

    def login_producer(self):
        self.client.login(username=self.producer_user.email, password="StrongProducerPass!2026")

    def checkout_order(self, products):
        self.login_customer()
        for product, quantity in products:
            CartItem.objects.create(customer=self.customer_user, product=product, quantity=quantity)
        response = self.client.post(
            reverse("checkout"),
            {
                "delivery_address": "45 Park Street, Bristol",
                "delivery_postcode": "BS1 5JG",
                "delivery_date": timezone.localdate() + timedelta(days=2),
                "special_instructions": "Leave by the front door",
                "payment_method": "test_card",
            },
        )
        self.assertEqual(response.status_code, 302)
        return Order.objects.latest("created_at")

    def test_tc001_producer_registration_creates_role_profile_and_hashed_password(self):
        response = self.client.post(
            reverse("producer_register"),
            {
                "business_name": "Bristol Valley Farm Resit",
                "contact_name": "Jane Smith",
                "email": "jane.smith@bristolvalleyfarm.com",
                "phone": "01179 123456",
                "business_address": "Bristol Valley Farm, Bristol",
                "postcode": "BS1 4DJ",
                "password1": "StrongProducerPass!2026",
                "password2": "StrongProducerPass!2026",
            },
        )

        self.assertRedirects(response, reverse("producer_dashboard"))
        user = User.objects.get(email="jane.smith@bristolvalleyfarm.com")
        self.assertNotEqual(user.password, "StrongProducerPass!2026")
        self.assertTrue(user.check_password("StrongProducerPass!2026"))
        self.assertEqual(user.producer_profile.business_name, "Bristol Valley Farm Resit")
        self.assertEqual(user.producer_profile.role, "producer")
        self.assertTrue(user.groups.filter(name="Producer").exists())

    def test_tc002_customer_registration_saves_delivery_address_and_permissions(self):
        response = self.client.post(
            reverse("customer_register"),
            {
                "full_name": "Robert Johnson",
                "email": "new.robert@example.com",
                "phone": "07700 900123",
                "delivery_address": "45 Park Street, Bristol",
                "postcode": "BS1 5JG",
                "accept_terms": "on",
                "password1": "StrongCustomerPass!2026",
                "password2": "StrongCustomerPass!2026",
            },
        )

        self.assertRedirects(response, reverse("customer_account"))
        user = User.objects.get(email="new.robert@example.com")
        self.assertEqual(user.customer_profile.delivery_address, "45 Park Street, Bristol")
        self.assertEqual(user.customer_profile.role, "customer")
        self.assertTrue(user.groups.filter(name="Customer").exists())

    def test_tc003_authenticated_producer_can_create_product_listing(self):
        self.login_producer()
        response = self.client.post(
            reverse("product_create"),
            {
                "name": "Organic Free Range Eggs",
                "category": self.eggs_category.pk,
                "description": "Fresh organic eggs from free-range hens, collected daily",
                "price": "3.50",
                "unit": "Dozen",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": "50",
                "allergen_info": "Contains eggs",
                "harvest_date": date.today(),
            },
        )

        self.assertRedirects(response, reverse("producer_dashboard"))
        product = Product.objects.get(name="Organic Free Range Eggs")
        self.assertEqual(product.producer, self.producer_user.producer_profile)
        self.assertTrue(product.is_customer_visible)

    def test_tc004_customers_can_browse_by_category_and_only_visible_products_show(self):
        Product.objects.create(
            producer=self.producer_user.producer_profile,
            category=self.vegetables,
            name="Hidden Beetroot",
            description="Unavailable product",
            price=Decimal("1.00"),
            unit="kg",
            availability=Product.AVAILABILITY_UNAVAILABLE,
            stock_quantity=Decimal("99.00"),
        )

        response = self.client.get(reverse("product_list"), {"category": "vegetables"})

        self.assertContains(response, "Organic Carrots")
        self.assertContains(response, "Organic Tomatoes")
        self.assertNotContains(response, "Fresh Milk")
        self.assertNotContains(response, "Hidden Beetroot")

    def test_tc005_search_matches_product_description_and_producer_and_handles_empty_results(self):
        response = self.client.get(reverse("product_list"), {"q": "tomatoes"})
        self.assertContains(response, "Organic Tomatoes")

        response = self.client.get(reverse("product_list"), {"q": "organic"})
        self.assertContains(response, "Organic Carrots")
        self.assertContains(response, "Organic Tomatoes")

        response = self.client.get(reverse("product_list"), {"q": "Hillside"})
        self.assertContains(response, "Fresh Milk")

        response = self.client.get(reverse("product_list"), {"q": "dragonfruit"})
        self.assertContains(response, "No results found.")

    def test_tc006_customer_can_add_products_to_cart_and_update_quantities(self):
        self.login_customer()
        self.client.post(reverse("cart_add", args=[self.carrots.pk]), {"quantity": "2"})
        self.client.post(reverse("cart_add", args=[self.milk.pk]), {"quantity": "3"})

        response = self.client.get(reverse("cart_detail"))
        self.assertContains(response, "Organic Carrots")
        self.assertContains(response, "Fresh Milk")
        self.assertContains(response, "Bristol Valley Farm")
        self.assertContains(response, "Hillside Dairy")

        item = CartItem.objects.get(customer=self.customer_user, product=self.carrots)
        self.client.post(reverse("cart_update", args=[item.pk]), {"quantity": "3"})
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("3.00"))

    def test_tc007_customer_can_checkout_single_producer_order_with_commission(self):
        order = self.checkout_order([(self.carrots, Decimal("2.00"))])

        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertEqual(order.total, Decimal("4.00"))
        self.assertEqual(order.commission, Decimal("0.20"))
        self.assertEqual(order.producer_total, Decimal("3.80"))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().producer, self.producer_user.producer_profile)
        self.assertFalse(CartItem.objects.filter(customer=self.customer_user).exists())

    def test_tc008_multi_producer_checkout_creates_single_order_with_producer_breakdown(self):
        order = self.checkout_order(
            [
                (self.carrots, Decimal("2.00")),
                (self.tomatoes, Decimal("1.00")),
                (self.milk, Decimal("2.00")),
            ]
        )

        self.assertEqual(order.items.values("producer").distinct().count(), 2)
        breakdown = order.producer_breakdown()
        self.assertIn("Bristol Valley Farm", breakdown)
        self.assertIn("Hillside Dairy", breakdown)
        self.assertEqual(order.total, Decimal("10.60"))
        self.assertEqual(order.commission, Decimal("0.53"))
        self.assertEqual(order.producer_total, Decimal("10.07"))

    def test_tc009_producer_can_view_only_their_incoming_order_items(self):
        order = self.checkout_order([(self.carrots, Decimal("2.00")), (self.milk, Decimal("2.00"))])
        self.client.logout()
        self.login_producer()

        response = self.client.get(reverse("producer_orders"))
        self.assertContains(response, order.order_number)
        self.assertContains(response, "Robert Johnson")

        response = self.client.get(reverse("producer_order_detail", args=[order.pk]))
        self.assertContains(response, "Organic Carrots")
        self.assertNotContains(response, "Fresh Milk")
        self.assertContains(response, "45 Park Street")

    def test_tc010_producer_updates_order_status_with_audit_history(self):
        order = self.checkout_order([(self.carrots, Decimal("2.00"))])
        self.client.logout()
        self.login_producer()

        response = self.client.post(
            reverse("producer_order_status", args=[order.pk]),
            {
                "status": Order.STATUS_CONFIRMED,
                "note": "Products will be prepared by delivery date",
            },
        )

        self.assertRedirects(response, reverse("producer_order_detail", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                changed_by=self.producer_user,
                status=Order.STATUS_CONFIRMED,
                note="Products will be prepared by delivery date",
            ).exists()
        )

    def test_customer_cannot_access_producer_product_creation(self):
        self.login_customer()
        response = self.client.get(reverse("product_create"))
        self.assertEqual(response.status_code, 403)

# Create your tests here.
