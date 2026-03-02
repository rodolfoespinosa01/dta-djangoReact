from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_message_messageattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="messageattachment",
            name="content_type",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="messageattachment",
            name="file_size",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="messageattachment",
            name="original_filename",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
