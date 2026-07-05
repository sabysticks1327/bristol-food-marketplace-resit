from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from marketplace.models import Category, CustomerProfile, ProducerProfile, Product


class Command(BaseCommand):
    help = "Seed demo users, categories, and products for TC-001 to TC-007 and TC-022."

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

        CustomerProfile.objects.update_or_create(
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
                "allergen_info": "Contains eggs",
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
                "allergen_info": "Contains milk",
                "harvest_date": None,
            },
        ]

        for product in products:
            defaults = product.copy()
            name = defaults.pop("name")
            producer = defaults.pop("producer")
            Product.objects.update_or_create(
                name=name,
                producer=producer,
                defaults=defaults,
            )

        self.stdout.write(self.style.SUCCESS("TC-001 to TC-007 and TC-022 demo data seeded."))
