from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from marketplace.models import CustomerProfile, ProducerProfile


class Command(BaseCommand):
    help = "Seed demo producer data for TC-001."

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

        ProducerProfile.objects.update_or_create(
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

        self.stdout.write(self.style.SUCCESS("TC-001 and TC-002 demo users seeded."))
