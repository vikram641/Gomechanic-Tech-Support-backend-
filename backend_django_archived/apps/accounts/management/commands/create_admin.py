import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import repository


class Command(BaseCommand):
    help = "Bootstrap the first admin account (there's no Django ORM superuser here)."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=False)

    def handle(self, *args, **options):
        password = options.get("password") or getpass.getpass("Admin password: ")
        try:
            user = repository.create_user(
                name=options["name"],
                email=options["email"],
                password=password,
                role="admin",
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Created admin '{user['email']}'."))
