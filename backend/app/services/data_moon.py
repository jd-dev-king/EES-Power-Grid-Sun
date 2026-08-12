from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from wsgiref import headers

import httpx

from app.core.config import get_settings

settings = get_settings()


def _url(path: str) -> str:
    return settings.data_moon_api_url.rstrip("/") + "/" + path.lstrip("/")


def build_tick_payload(rows: list[dict[str, Any]], minutes: float) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc)

    faults = [
        row for row in rows
        if row.get("fault_code")
    ]

    return {
        "system_key": settings.data_moon_system_key,
        "asset_id": None,
        "timestamp": generated_at.isoformat(),
        "source": "EES Power Grid Sun",
        "environment": settings.environment,
        "tags": {
            "event_type": "power_grid.simulation_tick",
            "record_count": len(rows),
            "tick_minutes": minutes,
            "fault_count": len(faults),
        },

        # Required Data Moon TelemetryEvent fields
        "metric": "power_grid.simulation_tick",
        "value": {
            "tick_minutes": minutes,
            "record_count": len(rows),
            "fault_count": len(faults),
            "records": rows,
        },

        "unit": "grid_snapshot",
        "severity": "warning" if faults else "normal",
    }


def forward_tick(rows: list[dict[str, Any]], minutes: float) -> dict[str, Any]:
    if not settings.data_moon_enabled:
        return {"status": "disabled", "forwarded": False}

    headers = {"Content-Type": "application/json"}

    if settings.data_moon_ingest_api_key:
        headers["X-EES-Ingest-Key"] = settings.data_moon_ingest_api_key

    payload = build_tick_payload(rows, minutes)
    try:
        response = httpx.post(
            _url(settings.data_moon_ingest_path),
            json=payload,
            headers=headers,
            timeout=settings.data_moon_timeout_seconds,
        )
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError:
            result = {"message": response.text[:300]}
        return {
            "status": "forwarded",
            "forwarded": True,
            "http_status": response.status_code,
            "endpoint": settings.data_moon_ingest_path,
            "response": result,
        }
    except httpx.HTTPError as exc:
        return {
            "status": "unavailable",
            "forwarded": False,
            "endpoint": settings.data_moon_ingest_path,
            "error": str(exc),
        }


def data_moon_health() -> dict[str, Any]:
    if not settings.data_moon_enabled:
        return {"status": "disabled", "online": False}
    try:
        response = httpx.get(
            _url(settings.data_moon_health_path),
            timeout=settings.data_moon_timeout_seconds,
        )
        response.raise_for_status()
        return {"status": "online", "online": True, "http_status": response.status_code}
    except httpx.HTTPError as exc:
        return {"status": "offline", "online": False, "error": str(exc)}
