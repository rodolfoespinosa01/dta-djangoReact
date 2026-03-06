from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0013_clientweightentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientprofile",
            name="theme_preference",
            field=models.CharField(default="light", max_length=20),
        ),
    ]
