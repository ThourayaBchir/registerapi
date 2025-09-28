from celery import shared_task


@shared_task(name="send_activation_email")
def send_activation_email(email: str, code: str) -> None:
    # TODO: integrate with email infrastructure.
    print(f"Sending activation code {code} to {email}")
