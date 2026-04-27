from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import users.client_area.models


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0018_clientfoodoverride_barcode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductImageSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(db_index=True, max_length=40)),
                ("provider_product_id", models.CharField(db_index=True, max_length=120)),
                ("barcode", models.CharField(blank=True, db_index=True, default="", max_length=80)),
                ("product_name", models.CharField(blank=True, default="", max_length=220)),
                ("brand", models.CharField(blank=True, default="", max_length=160)),
                ("image", models.FileField(upload_to=users.client_area.models.product_image_submission_upload_path)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_product_image_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="product_image_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Product Image Submission",
                "verbose_name_plural": "Product Image Submissions",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="productimagesubmission",
            index=models.Index(fields=["provider", "provider_product_id", "status"], name="product_img_provider_idx"),
        ),
        migrations.AddIndex(
            model_name="productimagesubmission",
            index=models.Index(fields=["barcode", "status"], name="product_img_barcode_idx"),
        ),
    ]
