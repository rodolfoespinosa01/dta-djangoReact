from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0019_productimagesubmission"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientfoodoverride",
            name="preparation_state",
            field=models.CharField(
                choices=[
                    ("raw", "Raw / uncooked"),
                    ("cooked", "Cooked"),
                    ("boiled", "Boiled"),
                    ("grilled", "Grilled"),
                    ("baked", "Baked"),
                    ("drained", "Drained / cooked"),
                    ("dry_uncooked", "Dry / uncooked"),
                    ("as_packaged", "As packaged"),
                    ("unknown", "Unknown"),
                ],
                db_index=True,
                default="as_packaged",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="clientfoodoverride",
            name="measurement_basis_label",
            field=models.CharField(blank=True, default="As packaged", max_length=80),
        ),
    ]
