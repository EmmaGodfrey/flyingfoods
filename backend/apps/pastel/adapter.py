"""Pastel adapter: the integration boundary between our system and Pastel.

get_adapter() returns the active implementation. Today that is always the
stub. When real credentials are configured, swap the return value here.
send_to_pastel() is a pure function — no Celery, no side effects beyond
writing a PastelSyncLog row.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from apps.core.models import OutboxRecord


class PastelError(Exception):
    """Raised by the adapter when Pastel returns an error or is unreachable."""


class PastelAdapter(Protocol):
    """Structural type for any Pastel implementation (stub or real HTTP)."""

    def post_movement(self, payload: dict) -> dict:
        """Send a movement payload and return the Pastel response."""
        ...


def get_adapter() -> PastelAdapter:
    """Return the active Pastel adapter.

    Returns the stub adapter for all environments until real Pastel
    credentials are configured. Swap this return value to plug in a real
    HTTP client.
    """
    from apps.pastel.stub import get_stub

    return get_stub()


def send_to_pastel(outbox_record: "OutboxRecord") -> bool:
    """Push one OutboxRecord to Pastel and record the outcome.

    Calls the active adapter's post_movement, then writes a PastelSyncLog
    row for the attempt (SUCCESS or FAILED) regardless of the outcome.
    Does not mutate the OutboxRecord's status or attempts — that is the
    caller's responsibility (tasks.py).

    Args:
        outbox_record: The OutboxRecord to push.

    Returns:
        True on success, False on failure.
    """
    from apps.pastel.models import PastelSyncLog

    adapter = get_adapter()
    payload = outbox_record.payload

    try:
        response = adapter.post_movement(payload)
        PastelSyncLog.objects.create(
            outbox=outbox_record,
            status=PastelSyncLog.Status.SUCCESS,
            request_payload=payload,
            response=response,
        )
        return True
    except PastelError as exc:
        PastelSyncLog.objects.create(
            outbox=outbox_record,
            status=PastelSyncLog.Status.FAILED,
            request_payload=payload,
            response={"error": str(exc)},
        )
        return False
