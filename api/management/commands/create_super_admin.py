from django.core.management.base import BaseCommand
from api.models import Utilizador


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        if not Utilizador.objects.filter(role="SUPER_ADMIN").exists():

            Utilizador.objects.create_superuser(
                username="superadmin",
                email="admin@sistema.gov",
                password="admin123",
                role="SUPER_ADMIN"
            )

            self.stdout.write(self.style.SUCCESS("Super Admin criado"))