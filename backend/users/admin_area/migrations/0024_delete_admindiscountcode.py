from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("admin_area", "0023_alter_plan_name"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AdminDiscountCode",
        ),
    ]
