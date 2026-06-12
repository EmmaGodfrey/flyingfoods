"""Preflight checker for DB connectivity before running Alembic migrations."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from urllib.parse import urlparse

from app.core.config import settings


def _parse_host_port(database_url: str) -> tuple[str, int]:
    parsed = urlparse(database_url)
    if not parsed.hostname:
        raise ValueError(f"Could not parse database hostname from URL: {database_url}")
    host = parsed.hostname
    port = parsed.port or 5432
    return host, port


def check_db_port(host: str, port: int, timeout_seconds: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True, f"Database port reachable at {host}:{port}."
    except OSError as exc:
        return False, f"Database not reachable at {host}:{port} ({exc.__class__.__name__}: {exc})."


def run_alembic_upgrade_head() -> int:
    command = [sys.executable, "-m", "alembic", "upgrade", "head"]
    process = subprocess.run(command, check=False)
    return int(process.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DB reachability, then run alembic upgrade head.")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check DB reachability and exit without running Alembic.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="TCP connection timeout in seconds for DB reachability check (default: 2.0).",
    )
    args = parser.parse_args()

    host, port = _parse_host_port(settings.database_url)
    ok, message = check_db_port(host, port, args.timeout)
    print(message)

    if not ok:
        print("Hint: start PostgreSQL first, then re-run this command.")
        return 2

    if args.check_only:
        print("Check-only mode: skipping Alembic run.")
        return 0

    print("Running Alembic migration to head...")
    return run_alembic_upgrade_head()


if __name__ == "__main__":
    raise SystemExit(main())
