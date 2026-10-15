from argparse import ArgumentParser
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.seeds.demo import FIXTURE, seed_demo


class Command(BaseCommand):
    help = "Load the demo fixture, schedule upcoming classes and grant starter credit packs. Safe to rerun."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--force", action="store_true", help="Allow running when DEBUG is False.")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to seed demo data with DEBUG=False. Pass --force to override.")

        report = seed_demo()

        if report.fixture_loaded:
            self.stdout.write(f"Fixture '{FIXTURE}' loaded (users and studios).")
        else:
            self.stdout.write(f"Fixture '{FIXTURE}' already present, skipped.")
        self.stdout.write(f"Classes created: {report.classes_created}")
        self.stdout.write(f"Credit packs granted: {report.packs_granted}")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
