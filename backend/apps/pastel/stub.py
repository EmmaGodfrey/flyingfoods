"""Pastel API stub: simulates Pastel accounting responses without a real connection.

This is the only adapter implementation for now. A real HTTP adapter will
replace get_adapter() return value when credentials are configured.
"""

import uuid
from decimal import Decimal
from typing import Any

from decouple import config

# Module-level override dict for tests: {(product_code, location): Decimal}
# Keys are (product_code: str, location: str) tuples.
_ON_HAND_OVERRIDES: dict[tuple[str, str], Decimal] = {}


def set_on_hand_override(product_code: str, location: str, qty: Decimal) -> None:
    """Inject a diverging on-hand value for a specific product/location pair.

    Used in tests to simulate Pastel having a different quantity than we do.
    Call clear_on_hand_overrides() to reset after the test.
    """
    _ON_HAND_OVERRIDES[(product_code, location)] = qty


def clear_on_hand_overrides() -> None:
    """Remove all injected on-hand overrides."""
    _ON_HAND_OVERRIDES.clear()


class PastelStub:
    """Simulates the Pastel accounting API for development and testing.

    Reads PASTEL_STUB_FAIL from the environment. When set to '1' or True,
    post_movement raises PastelError to simulate an outage. Otherwise it
    returns a fake success response with a generated reference.
    """

    def post_movement(self, payload: dict) -> dict:
        """Submit a stock movement to Pastel.

        Args:
            payload: The movement payload built by post_movements().

        Returns:
            dict with status and Pastel-assigned reference.

        Raises:
            PastelError: when PASTEL_STUB_FAIL=1 to simulate an outage.
        """
        should_fail = config("PASTEL_STUB_FAIL", default=False, cast=bool)
        if should_fail:
            from apps.pastel.adapter import PastelError
            raise PastelError("Pastel stub: simulated outage (PASTEL_STUB_FAIL=1).")
        return {"status": "ok", "ref": str(uuid.uuid4())}

    def get_on_hand(self, product_code: str, location: str) -> Decimal:
        """Return Pastel's current on-hand for a product at a location.

        By default, returns the same quantity we hold so reconciliation shows
        zero divergence. Tests may call set_on_hand_override() to inject a
        different value and trigger a real divergence.

        Args:
            product_code: The product's Pastel code.
            location: The location identifier.

        Returns:
            Decimal quantity from Pastel's perspective.
        """
        override_key = (product_code, location)
        if override_key in _ON_HAND_OVERRIDES:
            return _ON_HAND_OVERRIDES[override_key]

        # Default: query our own balance so recon shows no divergence.
        from apps.inventory.models import StockBalance
        from apps.masterdata.models import Product

        product = Product.objects.filter(pastel_code=product_code).first()
        if product is None:
            return Decimal("0")

        balance = (
            StockBalance.objects.filter(
                product=product, location__name=location
            )
            .values("qty_on_hand")
            .first()
        )
        return balance["qty_on_hand"] if balance else Decimal("0")


def get_stub() -> PastelStub:
    """Return the shared stub instance."""
    return PastelStub()
