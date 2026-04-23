import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from threadline.state_machine import EmailStatus
from threadline.models import EmailMessage
from threadline.services.workflow_config import (
    resolve_threadline_notification_channel,
)
from threadline.tasks.notifications import (
    build_email_failure_text,
    send_threadline_notification,
)

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
    Trigger failure notification when an email transitions into FAILED.
    """
    if created:
        logger.debug(
            f"New email created: {instance.id}, "
            f"skipping failure notification"
        )
        return

    # Get the old status that was captured in pre_save
    old_status = getattr(instance, "_old_status", None)

    if old_status is None or old_status == instance.status:
        logger.debug(
            f"Email {instance.id} status unchanged: {instance.status}"
        )
        return

    if instance.status != EmailStatus.FAILED.value:
        logger.debug(
            f"Email {instance.id} status changed {old_status} -> "
            f"{instance.status} but is not FAILED; skipping"
        )
        return

    logger.info(
        f"Email {instance.id} status changed: {old_status} -> "
        f"{instance.status}"
    )

    try:
        channel = resolve_threadline_notification_channel()
        language = (channel.config or {}).get("language") if channel else None
        text = build_email_failure_text(
            instance,
            old_status,
            instance.status,
            language=language,
        )
        send_threadline_notification.delay(
            text,
            "email_status",
            str(instance.id),
            user_id=instance.user_id,
        )
    except Exception as exc:
        logger.error(
            f"Failed to queue threadline failure notification for email "
            f"{instance.id}: {exc}"
        )
