from django.core.management.base import BaseCommand

from apps.configuration.seed import seed_defaults


class Command(BaseCommand):
    help = "Seed default dropdown values (user types, platforms, priorities, WhatsApp template keys, SLA rules)."

    def handle(self, *args, **options):
        created = seed_defaults()
        if not created:
            self.stdout.write("Nothing to seed — defaults already present.")
            return
        for item in created:
            self.stdout.write(self.style.SUCCESS(f"created {item}"))
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created)} config values."))
