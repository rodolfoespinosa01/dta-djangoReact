from django.urls import path
from users.client_area.views.dashboard import dashboard_view
from users.client_area.views.public_marketing import admin_public_marketing_page
from users.client_area.views.auth_flow import (
    client_dashboard,
    client_food_preferences,
    client_plan_action,
    client_settings_view,
    macro_access_preview,
    macro_access_questionnaire,
    macro_access_questionnaire_submit,
    pending_signup_preview,
    public_signup_quote,
    questionnaire_status_or_draft,
    questionnaire_submit,
    register_client,
    start_signup,
)
from users.client_area.views.token_login import ClientTokenObtainPairView
from users.client_area.views.google_login import client_google_login
from users.client_area.views.billing import (
    client_checkout_quote,
    client_checkout_sync,
    client_start_checkout_session,
    client_start_queued_checkout_session,
    client_stripe_webhook,
)
from users.client_area.views.meal_combo_public import (
    meal_combo_lookup,
    meal_combo_slot_options,
    meal_combo_starter_templates,
)
from users.client_area.views.meal_plan_generation import (
    client_meal_plan_day_detail,
    client_meal_plan_generation_job_status,
    client_meal_plan_generation_run_full,
    client_meal_plan_generation_run_week,
    client_meal_plan_generation_run_week_status,
    client_meal_plan_generation_step1_run,
)
from users.client_area.views.meal_recipe_suggestions import client_meal_plan_day_recipe_ideas

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('public/admin-page/<slug:slug>/', admin_public_marketing_page, name='admin_public_marketing_page'),
    path('public/meal-combo-options/', meal_combo_slot_options, name='client_meal_combo_slot_options'),
    path('public/meal-combo-lookup/', meal_combo_lookup, name='client_meal_combo_lookup'),
    path('public/meal-combo-starter-templates/', meal_combo_starter_templates, name='client_meal_combo_starter_templates'),
    path('signup/start/', start_signup, name='client_start_signup'),
    path('signup/quote/', public_signup_quote, name='client_signup_quote'),
    path('pending-signup/<str:token>/', pending_signup_preview, name='client_pending_signup_preview'),
    path('macro-access/<str:token>/', macro_access_preview, name='client_macro_access_preview'),
    path('macro-access/<str:token>/questionnaire/', macro_access_questionnaire, name='client_macro_access_questionnaire'),
    path('macro-access/<str:token>/questionnaire/submit/', macro_access_questionnaire_submit, name='client_macro_access_questionnaire_submit'),
    path('register/', register_client, name='client_register'),
    path('login/', ClientTokenObtainPairView.as_view(), name='client_login'),
    path('google_login/', client_google_login, name='client_google_login'),
    path('app/dashboard/', client_dashboard, name='client_app_dashboard'),
    path('app/settings/', client_settings_view, name='client_app_settings'),
    path('app/settings/checkout-quote/', client_checkout_quote, name='client_app_settings_checkout_quote'),
    path('app/settings/start-checkout/', client_start_checkout_session, name='client_app_settings_start_checkout'),
    path('app/settings/start-queued-checkout/', client_start_queued_checkout_session, name='client_app_settings_start_queued_checkout'),
    path('app/settings/checkout-sync/', client_checkout_sync, name='client_app_settings_checkout_sync'),
    path('app/settings/plan-action/', client_plan_action, name='client_app_plan_action'),
    path('stripe_webhook/', client_stripe_webhook, name='client_stripe_webhook'),
    path('app/food-preferences/', client_food_preferences, name='client_app_food_preferences'),
    path('app/meal-plan-generation/run/', client_meal_plan_generation_run_full, name='client_meal_plan_generation_run_full'),
    path('app/meal-plan-generation/run-week/', client_meal_plan_generation_run_week, name='client_meal_plan_generation_run_week'),
    path('app/meal-plan-generation/run-week/<str:batch_id>/status/', client_meal_plan_generation_run_week_status, name='client_meal_plan_generation_run_week_status'),
    path('app/meal-plan-generation/step1-run/', client_meal_plan_generation_step1_run, name='client_meal_plan_generation_step1_run'),
    path('app/meal-plan-generation/jobs/<int:job_id>/', client_meal_plan_generation_job_status, name='client_meal_plan_generation_job_status'),
    path('app/meal-plan-days/<str:day_of_week>/detailed/', client_meal_plan_day_detail, name='client_meal_plan_day_detail'),
    path('app/meal-plan-days/<str:day_of_week>/recipe-ideas/', client_meal_plan_day_recipe_ideas, name='client_meal_plan_day_recipe_ideas'),
    path('app/questionnaire/', questionnaire_status_or_draft, name='client_questionnaire_status_or_draft'),
    path('app/questionnaire/submit/', questionnaire_submit, name='client_questionnaire_submit'),
]
