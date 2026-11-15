from django.db import migrations, models
import django.db.models.deletion


def backfill_snapshots(apps, schema_editor):
    HealthBaseline = apps.get_model("baselines", "HealthBaseline")
    BaselineSnapshot = apps.get_model("baselines", "BaselineSnapshot")

    groups = {}
    for row in HealthBaseline.objects.all().order_by(
        "astronaut_id", "baseline_version"
    ):
        groups.setdefault(
            (row.astronaut_id, row.baseline_version), []
        ).append(row)

    for (astronaut_id, version), rows in groups.items():
        first = rows[0]
        status_summary = {}
        for row in rows:
            status_summary[row.baseline_status] = (
                status_summary.get(row.baseline_status, 0) + 1
            )

        starts = [row.sample_start for row in rows if row.sample_start]
        ends = [row.sample_end for row in rows if row.sample_end]

        snapshot = BaselineSnapshot.objects.create(
            astronaut_id=astronaut_id,
            version=version,
            baseline_kind=first.baseline_kind,
            window_days=first.window_days,
            rolling_window_days=first.rolling_window_days,
            before=None,
            data_start=min(starts) if starts else None,
            data_end=max(ends) if ends else None,
            reading_count=max(
                (row.sample_count for row in rows), default=0
            ),
            metric_count=len(rows),
            status_summary=status_summary,
            calculation_date=first.calculation_date,
        )

        HealthBaseline.objects.filter(
            pk__in=[row.pk for row in rows]
        ).update(snapshot_id=snapshot.pk)


def remove_snapshots(apps, schema_editor):
    HealthBaseline = apps.get_model("baselines", "HealthBaseline")
    BaselineSnapshot = apps.get_model("baselines", "BaselineSnapshot")

    HealthBaseline.objects.update(snapshot=None)
    BaselineSnapshot.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("baselines", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BaselineSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("astronaut_id", models.CharField(db_index=True, max_length=64)),
                ("version", models.PositiveIntegerField()),
                (
                    "baseline_kind",
                    models.CharField(
                        choices=[
                            ("RECENT", "Recent window"),
                            ("LONG_TERM", "Long-term history"),
                        ],
                        default="RECENT",
                        max_length=16,
                    ),
                ),
                (
                    "window_days",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("rolling_window_days", models.PositiveIntegerField(default=7)),
                ("before", models.DateTimeField(blank=True, null=True)),
                ("data_start", models.DateTimeField(blank=True, null=True)),
                ("data_end", models.DateTimeField(blank=True, null=True)),
                ("reading_count", models.PositiveIntegerField(default=0)),
                ("metric_count", models.PositiveIntegerField(default=0)),
                ("status_summary", models.JSONField(default=dict)),
                ("calculation_date", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["astronaut_id", "-version"],
                "indexes": [
                    models.Index(
                        fields=["astronaut_id", "-version"],
                        name="baselines_b_astrona_9b5b77_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("astronaut_id", "version"),
                        name="unique_snapshot_astronaut_version",
                    )
                ],
            },
        ),
        migrations.RenameField(
            model_name="healthbaseline",
            old_name="rolling_window",
            new_name="rolling_window_days",
        ),
        migrations.AddField(
            model_name="healthbaseline",
            name="baseline_kind",
            field=models.CharField(
                choices=[
                    ("RECENT", "Recent window"),
                    ("LONG_TERM", "Long-term history"),
                ],
                default="RECENT",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="healthbaseline",
            name="rolling_sample_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="healthbaseline",
            name="snapshot",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="baselines",
                to="baselines.baselinesnapshot",
            ),
        ),
        migrations.RunPython(backfill_snapshots, remove_snapshots),
        migrations.AlterField(
            model_name="healthbaseline",
            name="snapshot",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="baselines",
                to="baselines.baselinesnapshot",
            ),
        ),
        migrations.AddIndex(
            model_name="healthbaseline",
            index=models.Index(
                fields=["astronaut_id", "baseline_kind", "is_current"],
                name="baselines_kind_current_idx",
            ),
        ),
    ]
