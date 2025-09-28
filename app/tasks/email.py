from app.core.celery_app import celery_app


@celery_app.task
def send_activation_email(email: str, code: str) -> None:
    # TODO: integrate with email infrastructure.
    print(f"Sending activation code {code} to {email}")
