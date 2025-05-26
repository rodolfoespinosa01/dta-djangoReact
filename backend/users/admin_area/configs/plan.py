from django.contrib import admin  # 👉 gives access to register and customize models in the django admin
from users.admin_area.models import Plan  # 👉 imports the plan model from the admin_area app

class Plan(admin.ModelAdmin):  # 👉 defines how the plan model appears in the admin interface
    list_display = ('name', 'description', 'display_price', 'stripe_price_id')  
    # 👉 shows these fields as columns in the admin list view

    def display_price(self, obj):
        return f"${obj.price_cents / 100:.2f}"  # 👉 converts price from cents to formatted usd string
    display_price.short_description = 'Price (USD)'  # 👉 sets column header label in the admin table

# 👉 summary:
# customizes how subscription plans are displayed in the django admin panel.
# includes a clean price formatter and shows key plan info like name, description, and stripe id.
# used to manage admin-facing billing options tied to stripe pricing.