from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0015_clientpendingsignup_expires_at_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="DiscountCode",
        ),
    ]
