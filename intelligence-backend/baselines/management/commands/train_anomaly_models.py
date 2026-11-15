"""Train per-astronaut Isolation Forest anomaly models."""

from django.core.management.base import BaseCommand, CommandError

from baselines.models import HealthReading
from baselines.service import load_readings
from ml.anomaly_model import (
    DEFAULT_CONTAMINATION,
    DEFAULT_MIN_SAMPLES,
    DEFAULT_N_ESTIMATORS,
    InsufficientTrainingData,
    train_and_save_personal_anomaly_model,
)


class Command(BaseCommand):
    help = "Train personal Isolation Forest anomaly models from readings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--astronaut-id",
            dest="astronaut_id",
            help="Train only this astronaut instead of all astronauts.",
        )
        parser.add_argument(
            "--min-samples",
            type=int,
            default=DEFAULT_MIN_SAMPLES,
            help="Minimum usable readings required per astronaut.",
        )
        parser.add_argument(
            "--contamination",
            type=float,
            default=DEFAULT_CONTAMINATION,
            help="Expected proportion of anomalies in the training data.",
        )
        parser.add_argument(
            "--n-estimators",
            type=int,
            default=DEFAULT_N_ESTIMATORS,
            help="Number of trees in each Isolation Forest.",
        )

    def handle(self, *args, **options):
        astronaut_id = options.get("astronaut_id")

        if astronaut_id:
            astronaut_ids = [astronaut_id]
        else:
            astronaut_ids = list(
                HealthReading.objects
                .order_by("astronaut_id")
                .values_list("astronaut_id", flat=True)
                .distinct()
            )

        if not astronaut_ids:
            raise CommandError("No readings are available for training.")

        trained = 0
        skipped = 0

        for identifier in astronaut_ids:
            frame = load_readings(identifier)

            try:
                artifact, path = train_and_save_personal_anomaly_model(
                    identifier,
                    frame,
                    min_samples=options["min_samples"],
                    contamination=options["contamination"],
                    n_estimators=options["n_estimators"],
                )
            except InsufficientTrainingData as error:
                skipped += 1
                self.stderr.write(
                    self.style.WARNING(f"Skipped {identifier}: {error}")
                )
                continue

            trained += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Trained {identifier}: {artifact['sample_count']} "
                    f"readings, {len(artifact['feature_names'])} features "
                    f"-> {path}"
                )
            )

        self.stdout.write(
            f"Trained {trained} model(s), skipped {skipped}."
        )
