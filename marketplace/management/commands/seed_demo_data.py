from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from marketplace.models import Category, CustomerProfile, ProducerProfile, Product


class Command(BaseCommand):
    help = "Seed demo data for TC-001 to TC-010 demo flows."

    def handle(self, *args, **options):
        producer_group, _ = Group.objects.get_or_create(name="Producer")
        customer_group, _ = Group.objects.get_or_create(name="Customer")

        producer_user, _ = User.objects.get_or_create(
            username="jane.smith@bristolvalleyfarm.com",
            defaults={
                "email": "jane.smith@bristolvalleyfarm.com",
                "first_name": "Jane Smith",
            },
        )
        producer_user.set_password("StrongProducerPass!2026")
        producer_user.save()
        producer_user.groups.add(producer_group)
        producer, _ = ProducerProfile.objects.get_or_create(
            user=producer_user,
            defaults={
                "business_name": "Bristol Valley Farm",
                "contact_name": "Jane Smith",
                "phone": "01179 123456",
                "business_address": "Bristol Valley Farm, Bristol",
                "postcode": "BS1 4DJ",
            },
        )

        dairy_user, _ = User.objects.get_or_create(
            username="orders@hillsidedairy.example",
            defaults={"email": "orders@hillsidedairy.example", "first_name": "Hillside Dairy"},
        )
        dairy_user.set_password("StrongProducerPass!2026")
        dairy_user.save()
        dairy_user.groups.add(producer_group)
        dairy, _ = ProducerProfile.objects.get_or_create(
            user=dairy_user,
            defaults={
                "business_name": "Hillside Dairy",
                "contact_name": "Aisha Patel",
                "phone": "01179 654321",
                "business_address": "Hillside Dairy, Bristol",
                "postcode": "BS8 2AB",
            },
        )

        customer_user, _ = User.objects.get_or_create(
            username="robert.johnson@email.com",
            defaults={"email": "robert.johnson@email.com", "first_name": "Robert Johnson"},
        )
        customer_user.set_password("StrongCustomerPass!2026")
        customer_user.save()
        customer_user.groups.add(customer_group)
        CustomerProfile.objects.get_or_create(
            user=customer_user,
            defaults={
                "full_name": "Robert Johnson",
                "phone": "07700 900123",
                "delivery_address": "45 Park Street, Bristol",
                "postcode": "BS1 5JG",
                "accepted_terms": True,
            },
        )

        vegetables, _ = Category.objects.get_or_create(name="Vegetables", slug="vegetables")
        dairy_category, _ = Category.objects.get_or_create(name="Dairy Products", slug="dairy-products")
        eggs_category, _ = Category.objects.get_or_create(name="Dairy & Eggs", slug="dairy-eggs")

        Product.objects.get_or_create(
            producer=producer,
            name="Organic Carrots",
            defaults={
                "category": vegetables,
                "description": "Fresh organic carrots grown near Bristol.",
                "price": Decimal("2.00"),
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": Decimal("50"),
                "allergen_info": "",
                "harvest_date": date.today(),
            },
        )
        Product.objects.get_or_create(
            producer=producer,
            name="Organic Tomatoes",
            defaults={
                "category": vegetables,
                "description": "Organic tomatoes with rich flavour.",
                "price": Decimal("3.00"),
                "unit": "kg",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": Decimal("20"),
                "allergen_info": "",
                "harvest_date": date.today(),
            },
        )
        Product.objects.get_or_create(
            producer=dairy,
            name="Fresh Milk",
            defaults={
                "category": dairy_category,
                "description": "Fresh local milk from Hillside Dairy.",
                "price": Decimal("1.80"),
                "unit": "litre",
                "availability": Product.AVAILABILITY_AVAILABLE,
                "stock_quantity": Decimal("80"),
                "allergen_info": "Contains: Milk",
                "harvest_date": date.today(),
            },
        )
        Product.objects.get_or_create(
            producer=producer,
            name="Organic Free Range Eggs",
            defaults={
                "category": eggs_category,
                "description": "Fresh organic eggs from free-range hens, collected daily.",
                "price": Decimal("3.50"),
                "unit": "dozen",
                "availability": Product.AVAILABILITY_IN_SEASON,
                "stock_quantity": Decimal("50"),
                "allergen_info": "Contains eggs",
                "harvest_date": date.today(),
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
