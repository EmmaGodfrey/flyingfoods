# Generated migration for Pastel integration models.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0002_initial"),
        ("masterdata", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReconciliationRun",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("run_date", models.DateField()),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Reconciliation Run",
                "verbose_name_plural": "Reconciliation Runs",
                "ordering": ["-run_date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ReconciliationLine",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "our_on_hand",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "pastel_on_hand",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "divergence",
                    models.DecimalField(decimal_places=3, max_digits=12),
                ),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reconciliation_lines",
                        to="masterdata.location",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reconciliation_lines",
                        to="masterdata.product",
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="pastel.reconciliationrun",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reconciliation Line",
                "verbose_name_plural": "Reconciliation Lines",
                "ordering": ["run", "product"],
            },
        ),
        migrations.CreateModel(
            name="PastelSyncLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("attempted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("SUCCESS", "Success"), ("FAILED", "Failed")],
                        max_length=10,
                    ),
                ),
                ("request_payload", models.JSONField()),
                ("response", models.JSONField(blank=True, null=True)),
                (
                    "outbox",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sync_logs",
                        to="core.outboxrecord",
                    ),
                ),
            ],
            options={
                "verbose_name": "Pastel Sync Log",
                "verbose_name_plural": "Pastel Sync Logs",
                "ordering": ["-attempted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="pastelsynclog",
            index=models.Index(
                fields=["status", "attempted_at"],
                name="pastel_log_status_at_idx",
            ),
        ),
    ]
