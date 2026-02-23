from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("client_area", "0002_clientmacroaccesslink"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientmacroaccesslink",
            name="questionnaire_answers_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="clientmacroaccesslink",
            name="questionnaire_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="clientmacroaccesslink",
            name="questionnaire_current_step",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="clientmacroaccesslink",
            name="questionnaire_status",
            field=models.CharField(choices=[("not_started", "Not Started"), ("in_progress", "In Progress"), ("completed", "Completed")], db_index=True, default="not_started", max_length=20),
        ),
    ]

