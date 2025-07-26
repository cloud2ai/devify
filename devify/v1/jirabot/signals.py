import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from v1.jirabot.models import EmailMessage
from v1.jirabot.tasks.notifications import send_webhook_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=EmailMessage)
def notify_email_status_change(sender, instance, created, **kwargs):
    """
    Simple signal handler that triggers notification task for any status change.
    All business logic is handled in the task.
    """
    if created:
        logger.debug(f"New email created: {instance.id}, "
                     f"skipping notification")
        return

    try:
        # Get the old status from database
        old_instance = EmailMessage.objects.get(pk=instance.pk)
        old_status = old_instance.status
    except EmailMessage.DoesNotExist:
        logger.warning(f"Email {instance.id} not found in database, "
                       f"skipping notification")
        return

    # Only trigger notification if status actually changed
    if old_status != instance.status:
        logger.info(f"Email {instance.id} status changed: {old_status} -> "
                    f"{instance.status}")

        # Trigger async webhook notification - let the task
        # handle all business logic
        send_webhook_notification.delay(
            instance.id,
            old_status,
            instance.status
        )
    else:
        logger.debug(f"Email {instance.id} status "
                     f"unchanged: {instance.status}")