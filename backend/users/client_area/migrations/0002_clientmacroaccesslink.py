from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("admin_area", "0019_adminidentity_subdomain_fields"),
        ("client_area", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientMacroAccessLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("token", models.CharField(db_index=True, max_length=128, unique=True)),
                ("sale_channel", models.CharField(choices=[("dta_direct", "DTA Direct"), ("admin_white_label", "Admin White Label")], default="admin_white_label", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_opened_at", models.DateTimeField(blank=True, null=True)),
                ("admin", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="client_macro_access_links", to="admin_area.adminidentity")),
            ],
            options={
                "verbose_name": "Client Macro Access Link",
                "verbose_name_plural": "Client Macro Access Links",
                "ordering": ("-created_at",),
            },
        ),
    ]

