from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0017_clientfoodoverride"),
    ]

    operations = [
        migrations.AlterField(
            model_name="clientfoodoverride",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("usda", "USDA FoodData Central"),
                    ("open_food_facts", "Open Food Facts"),
                ],
                db_index=True,
                default="usda",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="clientfoodoverride",
            name="barcode",
            field=models.CharField(blank=True, db_index=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="clientfoodoverride",
            name="image_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="clientfoodoverride",
            name="ingredients",
            field=models.TextField(blank=True, default=""),
        ),
    ]
