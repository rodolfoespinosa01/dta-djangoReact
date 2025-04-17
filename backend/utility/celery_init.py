from celery import Celery

# 👇 Called automatically when Celery is finalized
def setup_celery_tasks(app: Celery):
    @app.on_after_finalize.connect
    def import_custom_tasks(sender, **kwargs):
        # ✅ Import custom tasks to register with Celery
        import users.tasks.admin.auto_upgrade_admin_trial
