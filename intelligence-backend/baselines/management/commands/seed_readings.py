"""Seed the intelligence database with deterministic sample readings."""

import pandas as pd
from django.core.management.base import BaseCommand

from baselines.models import HealthReading
from ml.metrics import METRIC_COLUMNS
from sample_data import generate_sample_data


class Command(BaseCommand):
    help = "Load simulated astronaut health readings into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of daily readings per astronaut.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing readings before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = HealthReading.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing records.")

        frame = generate_sample_data(days=options["days"])

        objects = []
        for record in frame.to_dict("records"):
            values = {
                metric: (
                    None if pd.isna(record[metric]) else float(record[metric])
                )
                for metric in METRIC_COLUMNS
            }
            objects.append(HealthReading(
                astronaut_id=record["astronaut_id"],
                recorded_at=record["recorded_at"],
                source="simulated",
                **values,
            ))

        before = HealthReading.objects.count()
        HealthReading.objects.bulk_create(objects, ignore_conflicts=True)
        created = HealthReading.objects.count() - before

        self.stdout.write(self.style.SUCCESS(
            f"Inserted {created} new readings "
            f"({len(objects)} generated, duplicates skipped)."
        ))
