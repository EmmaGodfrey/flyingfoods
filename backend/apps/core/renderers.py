"""Global response envelope: {"success": true, "data": ...} on every endpoint."""

from typing import Any, Mapping, Optional

from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    """Wrap successful payloads in the project-wide envelope.

    Error payloads are already shaped by `envelope_exception_handler`,
    which marks them with the `_enveloped` key so they pass through.
    """

    def render(
        self,
        data: Any,
        accepted_media_type: Optional[str] = None,
        renderer_context: Optional[Mapping[str, Any]] = None,
    ) -> bytes:
        if isinstance(data, dict) and data.get("_enveloped") is True:
            payload = {key: value for key, value in data.items() if key != "_enveloped"}
        else:
            payload = {"success": True, "data": data}
        return super().render(payload, accepted_media_type, renderer_context)
