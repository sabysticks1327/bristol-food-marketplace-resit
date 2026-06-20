from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from marketplace.models import ProducerProfile


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

        self.stdout.write(self.style.SUCCESS("TC-001 demo producer seeded."))
