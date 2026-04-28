from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0020_clientfoodoverride_measurement_basis"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientpendingsignup",
            name="questionnaire_answers_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="clientpendingsignup",
            name="questionnaire_results_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
