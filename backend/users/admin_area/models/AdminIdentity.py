from django.db import models
import uuid


class AdminIdentity(models.Model):
    # Theming fields
    marketing_theme = models.CharField(max_length=40, null=True, blank=True, help_text="Theme name for this admin's marketing page (e.g. 'dark', 'red', 'custom').")
    custom_css_url = models.URLField(max_length=500, null=True, blank=True, help_text="URL to a custom CSS file for this admin's marketing page.")
    adminID = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    admin_email = models.EmailField(unique=True)
    subdomain_slug = models.CharField(max_length=40, unique=True, null=True, blank=True)
    subdomain_locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Custom marketing fields
    marketing_headline = models.CharField(max_length=200, null=True, blank=True, help_text="Custom marketing headline for this admin's page.")
    marketing_subheadline = models.CharField(max_length=300, null=True, blank=True, help_text="Custom marketing subheadline for this admin's page.")
    marketing_image_url = models.URLField(max_length=500, null=True, blank=True, help_text="URL to a custom marketing image for this admin's page.")
    marketing_html = models.TextField(null=True, blank=True, help_text="Optional custom HTML for this admin's marketing page.")

    def __str__(self):
        return f"{self.admin_email} ({self.adminID})"
