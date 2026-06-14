"""Write services for notifications: single-user and role fan-out."""

from typing import Any, Optional

from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.notifications.models import Notification


def notify_user(
    recipient: Any,
    kind: str,
    body: str,
    subject: Optional[models.Model] = None,
) -> Notification:
    """Create and return one notification addressed to a single recipient.

    Args:
        recipient: The User instance who should receive this notification.
        kind: A Notification.Kind choice string.
        body: Human-readable message text.
        subject: Optional model instance used to build the GenericFK deep-link.

    Returns:
        The newly created Notification row.
    """
    subject_type = None
    subject_id = None
    if subject is not None:
        subject_type = ContentType.objects.get_for_model(type(subject))
        subject_id = subject.pk

    return Notification.objects.create(
        recipient=recipient,
        kind=kind,
        body=body,
        subject_type=subject_type,
        subject_id=subject_id,
    )


def notify_role(
    role: str,
    kind: str,
    body: str,
    subject: Optional[models.Model] = None,
) -> list[Notification]:
    """Fan out one notification per active user holding the given role.

    Args:
        role: A User.Role choice string (e.g. "MANAGER").
        kind: A Notification.Kind choice string.
        body: Human-readable message text.
        subject: Optional model instance for the GenericFK deep-link.

    Returns:
        List of created Notification rows, one per matching active user.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    recipients = User.objects.filter(role=role, is_active=True)

    subject_type = None
    subject_id = None
    if subject is not None:
        subject_type = ContentType.objects.get_for_model(type(subject))
        subject_id = subject.pk

    notifications = [
        Notification(
            recipient=user,
            kind=kind,
            body=body,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        for user in recipients
    ]
    return Notification.objects.bulk_create(notifications)
