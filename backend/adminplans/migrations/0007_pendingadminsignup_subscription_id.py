# Generated by Django 5.2 on 2025-04-15 06:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminplans", "0006_adminprofile_next_billing_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="pendingadminsignup",
            name="subscription_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
