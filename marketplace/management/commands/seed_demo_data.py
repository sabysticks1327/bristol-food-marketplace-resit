from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from marketplace.models import (
    Category,
    CustomerProfile,
    Order,
    OrderItem,
    OrderStatusHistory,
    PaymentRecord,
    ProducerProfile,
    Product,
    quantize_money,
)


class Command(BaseCommand):
    help = "Seed demo users, products, orders, and security data for implemented test cases."

    def handle(self, *args, **options):
        producer_group, _ = Group.objects.get_or_create(name="Producer")
        producer_user, _ = User.objects.get_or_create(
            username="jane.smith@bristolvalleyfarm.com",
            defaults={
                "email": "jane.smith@bristolvalleyfarm.com",
                "first_name": "Jane Smith",
            },
        )
        producer_user.email = "jane.smith@bristolvalleyfarm.com"
        producer_user.first_name = "Jane Smith"
        producer_user.set_password("StrongProducerPass!2026")
        producer_user.save()
        producer_user.groups.add(producer_group)

        bristol_valley, _ = ProducerProfile.objects.update_or_create(
            user=producer_user,
            defaults={
                "business_name": "Bristol Valley Farm",
                "contact_name": "Jane Smith",
                "phone": "01179 123456",
                "business_address": "Bristol Valley Farm, Bristol",
                "postcode": "BS1 4DJ",
                "role": ProducerProfile.ROLE_NAME,
                "verified": True,
            },
        )

        hillside_user, _ = User.objects.get_or_create(
            username="tom.harris@hillsidedairy.co.uk",
            defaults={
                "email": "tom.harris@hillsidedairy.co.uk",
                "first_name": "Tom Harris",
            },
        )
        hillside_user.email = "tom.harris@hillsidedairy.co.uk"
        hillside_user.first_name = "Tom Harris"
        hillside_user.set_password("StrongProducerPass!2026")
        hillside_user.save()
        hillside_user.groups.add(producer_group)

        hillside_dairy, _ = ProducerProfile.objects.update_or_create(
            user=hillside_user,
            defaults={
                "business_name": "Hillside Dairy",
                "contact_name": "Tom Harris",
                "phone": "01179 654321",
                "business_address": "Hillside Dairy, North Somerset",
                "postcode": "BS40 5AA",
                "role": ProducerProfile.ROLE_NAME,
                "verified": True,
            },
        )

        customer_group, _ = Group.objects.get_or_create(name="Customer")
        customer_user, _ = User.objects.get_or_create(
            username="robert.johnson@email.com",
            defaults={
                "email": "robert.johnson@email.com",
                "first_name": "Robert Johnson",
            },
        )
        customer_user.email = "robert.johnson@email.com"
        customer_user.first_name = "Robert Johnson"
        customer_user.set_password("StrongCustomerPass!2026")
        customer_user.save()
        customer_user.groups.add(customer_group)

        customer, _ = CustomerProfile.objects.update_or_create(
            user=customer_user,
            defaults={
                "full_name": "Robert Johnson",
                "phone": "07700 900123",
                "delivery_address": "45 Park Street, Bristol",
                "postcode": "BS1 5JG",
                "role": CustomerProfile.ROLE_NAME,
                "accepted_terms": True,
            },
        )

        vegetables, _ = Category.objects.get_or_create(
            slug="vegetables",
            defaults={"name": "Vegetables"},
        )
        dairy_products, _ = Category.objects.get_or_create(
            slug="dairy-products",
            defaults={"name": "Dairy Products"},
        )
        dairy_eggs, _ = Category.objects.get_or_create(
            slug="dairy-eggs",
            defaults={"name": "Dairy & Eggs"},
        )
        bakery, _ = Category.objects.get_or_create(
            slug="bakery",
            defaults={"name": "Bakery"},
        )
        fruit, _ = Category.objects.get_or_create(
            slug="fruit",
            defaults={"name": "Fruit"},
        )

        products = [
            {
                "producer": bristol_valley,
                "category": vegetables,
                "name": "Organic Carrots",
                "description": "Fresh organic carrots grown near Bristol.",
                "price": Decimal("2.00"),
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": Decimal("50.00"),
                "allergen_info": "No common allergens",
                "organic_certified": True,
                "certification_body": "Soil Association",
                "certification_number": "SA-BVF-001",
                "harvest_date": date(2026, 7, 1),
            },
            {
                "producer": bristol_valley,
                "category": vegetables,
                "name": "Organic Tomatoes",
                "description": "Sweet seasonal tomatoes for salads and sauces.",
                "price": Decimal("3.00"),
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": Decimal("20.00"),
                "allergen_info": "No common allergens",
                "organic_certified": True,
                "certification_body": "Soil Association",
                "certification_number": "SA-BVF-002",
                "harvest_date": date(2026, 7, 2),
            },
            {
                "producer": bristol_valley,
                "category": dairy_eggs,
                "name": "Organic Free Range Eggs",
                "description": "Free range eggs from a local organic smallholding.",
                "price": Decimal("3.50"),
                "unit": "dozen",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": Decimal("50.00"),
                "allergen_info": "Eggs",
                "organic_certified": True,
                "certification_body": "Organic Farmers & Growers",
                "certification_number": "OFG-BVF-003",
                "harvest_date": None,
            },
            {
                "producer": hillside_dairy,
                "category": dairy_products,
                "name": "Fresh Milk",
                "description": "Whole milk from Hillside Dairy.",
                "price": Decimal("1.80"),
                "unit": "litre",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": Decimal("35.00"),
                "allergen_info": "Milk",
                "organic_certified": False,
                "certification_body": "",
                "certification_number": "",
                "harvest_date": None,
            },
            {
                "producer": hillside_dairy,
                "category": dairy_products,
                "name": "Cheddar Cheese",
                "description": "Mature cheddar made with local milk.",
                "price": Decimal("4.20"),
                "unit": "block",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": Decimal("12.00"),
                "allergen_info": "Milk",
                "organic_certified": False,
                "certification_body": "",
                "certification_number": "",
                "harvest_date": None,
            },
            {
                "producer": bristol_valley,
                "category": bakery,
                "name": "Walnut Bread",
                "description": "Fresh bakery loaf with walnuts.",
                "price": Decimal("3.80"),
                "unit": "loaf",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": Decimal("8.00"),
                "allergen_info": "Wheat (Gluten), Nuts (Walnuts)",
                "organic_certified": True,
                "certification_body": "Soil Association",
                "certification_number": "SA-BVF-004",
                "harvest_date": None,
            },
            {
                "producer": bristol_valley,
                "category": fruit,
                "name": "Fresh Apples",
                "description": "Crisp local orchard apples.",
                "price": Decimal("2.60"),
                "unit": "kg",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": Decimal("30.00"),
                "allergen_info": "No common allergens",
                "organic_certified": True,
                "certification_body": "Soil Association",
                "certification_number": "SA-BVF-005",
                "harvest_date": None,
            },
        ]

        saved_products = {}
        for product in products:
            defaults = product.copy()
            name = defaults.pop("name")
            producer = defaults.pop("producer")
            saved_product, _ = Product.objects.update_or_create(
                name=name,
                producer=producer,
                defaults=defaults,
            )
            saved_products[name] = saved_product

        demo_orders = [
            ("BFM-DEMO-001", saved_products["Organic Carrots"], Decimal("2.00"), 2),
            ("BFM-DEMO-002", saved_products["Organic Tomatoes"], Decimal("1.00"), 3),
            ("BFM-DEMO-003", saved_products["Walnut Bread"], Decimal("1.00"), 4),
        ]

        for order_number, product, quantity, delivery_offset in demo_orders:
            subtotal = quantize_money(product.price * quantity)
            order, _ = Order.objects.update_or_create(
                order_number=order_number,
                defaults={
                    "customer": customer,
                    "producer": product.producer,
                    "delivery_address": customer.delivery_address,
                    "delivery_postcode": customer.postcode,
                    "delivery_date": timezone.localdate() + timedelta(days=delivery_offset),
                    "special_instructions": "Demo order for producer preparation workflow.",
                    "status": Order.STATUS_PENDING,
                    "subtotal": subtotal,
                    "commission_amount": quantize_money(subtotal * Decimal("0.05")),
                    "producer_payment_amount": quantize_money(subtotal * Decimal("0.95")),
                },
            )
            order.items.all().delete()
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
            PaymentRecord.objects.update_or_create(
                order=order,
                defaults={
                    "provider": "test_sandbox",
                    "transaction_reference": f"TEST-{order.order_number}",
                    "amount": subtotal,
                    "status": PaymentRecord.STATUS_SUCCESS,
                },
            )
            OrderStatusHistory.objects.get_or_create(
                order=order,
                status=Order.STATUS_PENDING,
                defaults={"note": "Demo order created."},
            )

        previous_week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday() + 7)
        settlement_orders = [
            ("BFM-SETTLE-001", saved_products["Organic Carrots"], Decimal("3.00"), 1),
            ("BFM-SETTLE-002", saved_products["Walnut Bread"], Decimal("2.00"), 3),
        ]

        for order_number, product, quantity, day_offset in settlement_orders:
            subtotal = quantize_money(product.price * quantity)
            order, _ = Order.objects.update_or_create(
                order_number=order_number,
                defaults={
                    "customer": customer,
                    "producer": product.producer,
                    "delivery_address": customer.delivery_address,
                    "delivery_postcode": customer.postcode,
                    "delivery_date": previous_week_start + timedelta(days=day_offset),
                    "special_instructions": "Delivered order for weekly settlement demo.",
                    "status": Order.STATUS_DELIVERED,
                    "subtotal": subtotal,
                    "commission_amount": quantize_money(subtotal * Decimal("0.05")),
                    "producer_payment_amount": quantize_money(subtotal * Decimal("0.95")),
                },
            )
            order.items.all().delete()
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
            PaymentRecord.objects.update_or_create(
                order=order,
                defaults={
                    "provider": "test_sandbox",
                    "transaction_reference": f"TEST-{order.order_number}",
                    "amount": subtotal,
                    "status": PaymentRecord.STATUS_SUCCESS,
                },
            )
            OrderStatusHistory.objects.get_or_create(
                order=order,
                status=Order.STATUS_DELIVERED,
                defaults={"note": "Demo delivered order for settlement."},
            )

        self.stdout.write(self.style.SUCCESS("Implemented test-case demo data seeded."))
