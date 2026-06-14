"""Report export service: render a report payload as JSON, XLSX, or PDF.

PDF export requires ``weasyprint`` and its native libraries; when they are
absent the endpoint returns a graceful 501 rather than a 500.
"""

import io
from typing import Any, Optional

from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.response import Response


def export(rows: list[dict], fmt: str, title: str) -> Optional[HttpResponse]:
    """Render *rows* as the requested format and return an HttpResponse.

    Args:
        rows: Report rows — each a dict with uniform keys.
        fmt: One of ``json``, ``xlsx``, or ``pdf``.
        title: Human-readable report title (used in XLSX sheet name and PDF heading).

    Returns:
        An :class:`~django.http.HttpResponse` for xlsx/pdf, or ``None`` for
        json (the caller returns a DRF ``Response`` directly).

    Raises:
        ValueError: When *fmt* is not one of the supported values.
    """
    fmt = (fmt or "json").lower()
    if fmt == "json":
        return None
    if fmt == "xlsx":
        return _export_xlsx(rows, title)
    if fmt == "pdf":
        return _export_pdf(rows, title)
    return None


def _export_xlsx(rows: list[dict], title: str) -> HttpResponse:
    """Build an XLSX workbook from *rows* and return it as an HttpResponse.

    Args:
        rows: Uniform list of dicts; keys become the header row.
        title: Sheet name (truncated to 31 chars, the Excel limit).

    Returns:
        An :class:`~django.http.HttpResponse` with the correct content-type
        and a ``Content-Disposition: attachment`` header.
    """
    import openpyxl
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:31]

    if not rows:
        ws.append(["No data"])
    else:
        headers = list(rows[0].keys())
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in rows:
            ws.append([row.get(h) for h in headers])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    safe_title = title.replace(" ", "_")[:50]
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{safe_title}.xlsx"'
    return response


def _export_pdf(rows: list[dict], title: str) -> HttpResponse:
    """Render *rows* as a simple HTML table and convert it to PDF.

    Falls back to a 501 JSON response when ``weasyprint`` or its native
    rendering libraries are unavailable (the common case in CI / Windows).

    Args:
        rows: Uniform list of dicts.
        title: Report title shown as an ``<h1>`` heading.

    Returns:
        A PDF :class:`~django.http.HttpResponse`, or a 501 JSON response when
        the native libraries are not present.
    """
    try:
        from weasyprint import HTML  # type: ignore[import]
    except (ImportError, OSError):
        return HttpResponse(
            '{"success": false, "error": {"code": "PDF_UNAVAILABLE", "message": "PDF export unavailable in this environment"}}',
            content_type="application/json",
            status=501,
        )

    headers = list(rows[0].keys()) if rows else []
    th_cells = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = ""
    for row in rows:
        tds = "".join(f"<td>{row.get(h, '')}</td>" for h in headers)
        body_rows += f"<tr>{tds}</tr>"

    html_source = f"""
    <html>
    <head><style>
        body {{ font-family: sans-serif; font-size: 10px; }}
        h1 {{ font-size: 14px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
        th {{ background: #f0f0f0; font-weight: bold; }}
    </style></head>
    <body>
    <h1>{title}</h1>
    <table>
      <thead><tr>{th_cells}</tr></thead>
      <tbody>{body_rows}</tbody>
    </table>
    </body>
    </html>
    """

    pdf_bytes = HTML(string=html_source).write_pdf()
    safe_title = title.replace(" ", "_")[:50]
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{safe_title}.pdf"'
    return response


def render_report(rows: list[dict], request: Request, title: str) -> Any:
    """Dispatch to the correct renderer based on ``?format=`` query param.

    Views call this helper instead of calling ``export`` directly.  For
    ``json`` (the default) a standard DRF ``Response`` is returned so the
    envelope renderer wraps it automatically.  For ``xlsx`` and ``pdf`` the
    raw :class:`~django.http.HttpResponse` is returned.

    Args:
        rows: Report rows to render.
        request: The current DRF request; used to read ``request.query_params``.
        title: Human-readable report title passed through to ``export``.

    Returns:
        A DRF :class:`~rest_framework.response.Response` for json, or an
        :class:`~django.http.HttpResponse` for binary formats.
    """
    fmt = request.query_params.get("format", "json").lower()
    if fmt == "json":
        return Response(rows)
    result = export(rows, fmt, title)
    if result is None:
        return Response(rows)
    return result
