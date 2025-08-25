import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from threadline.models import EmailMessage
from threadline.tasks.notifications import send_webhook_notification

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=EmailMessage)
def capture_old_status(sender, instance, **kwargs):
    """
    Capture the old status before saving for comparison.
    """
    if instance.pk:  # Only for existing instances
        try:
            old_instance = EmailMessage.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except EmailMessage.DoesNotExist:
            instance._old_status = None


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

    # Get the old status that was captured in pre_save
    old_status = getattr(instance, '_old_status', None)

    if old_status is not None and old_status != instance.status:
        logger.info(f"Email {instance.id} status changed: {old_status} -> "
                    f"{instance.status}")

        # Trigger async webhook notification - let the task
        # handle all business logic
        try:
            send_webhook_notification.delay(
                instance.id,
                old_status,
                instance.status
            )
        except Exception as e:
            logger.error(f"Failed to queue webhook notification "
                         f"for email {instance.id}: {e}")
    else:
        logger.debug(f"Email {instance.id} status "
                     f"unchanged: {instance.status}")