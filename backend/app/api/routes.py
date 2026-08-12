import httpx
from datetime import datetime, timedelta, timezone
from math import sqrt

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.api import TelemetryIn, DiagnosticIn, ForecastRequest, SimulationTickRequest
from app.services.simulator import run_tick
from app.services.data_moon import forward_tick, data_moon_health
from app.services.queries import current_snapshot
from app.analytics.forecast import train_and_predict

router = APIRouter(prefix="/api/v1")
settings = get_settings()

def require_key(x_api_key: str | None = Header(default=None)):
    if settings.api_key != "change-me" and x_api_key != settings.api_key:
        raise HTTPException(401, "Invalid API key")

@router.get("/system/current")
def system_current(db: Session = Depends(get_db)):
    return current_snapshot(db)

@router.get("/assets")
def assets(facility: str | None = None, db: Session = Depends(get_db)):
    params = {}
    where = ""
    if facility:
        where = "WHERE LOWER(COALESCE(gn.location_name, 'EES Campus')) = LOWER(:facility)"
        params["facility"] = facility
    rows = db.execute(text(f"""
        SELECT
            gn.node_id, gn.node_code, gn.node_name, gn.node_type,
            gn.nominal_voltage_v, gn.location_name, gn.criticality,
            COALESCE(SUM(lc.rated_demand_kw), 0) AS rated_power_kw
        FROM power_grid.grid_nodes gn
        LEFT JOIN power_grid.load_centers lc ON lc.node_id = gn.node_id
        {where}
        GROUP BY gn.node_id
        ORDER BY gn.node_code
    """), params).mappings().all()
    return [{
        "asset_id": str(r["node_id"]),
        "code": r["node_code"],
        "name": r["node_name"],
        "area": r["location_name"] or "EES Campus",
        "type": r["node_type"],
        "rated_power_kw": float(r["rated_power_kw"] or 0),
        "voltage_v": float(r["nominal_voltage_v"] or 0),
        "critical": r["criticality"] in ("high", "critical"),
    } for r in rows]

@router.post("/power/telemetry", dependencies=[Depends(require_key)])
def ingest_telemetry(payload: TelemetryIn, db: Session = Depends(get_db)):
    node = db.execute(text("""
        SELECT DISTINCT gn.node_id, gn.node_code, gn.nominal_voltage_v, gn.phase_configuration
        FROM power_grid.grid_nodes gn
        LEFT JOIN power_grid.load_centers lc ON lc.node_id = gn.node_id
        WHERE gn.node_code = :code OR lc.load_code = :code
        LIMIT 1
    """), {"code": payload.asset_code}).mappings().one_or_none()
    if not node:
        raise HTTPException(404, "Power Grid node/load center not found")

    apparent = payload.real_power_kw / max(payload.power_factor, 0.1)
    reactive = max(apparent ** 2 - payload.real_power_kw ** 2, 0) ** 0.5
    voltage_status = "normal"
    nominal_v = float(node["nominal_voltage_v"] or 0)
    if nominal_v > 0:
        dev = (payload.voltage_v - nominal_v) / nominal_v
        if abs(dev) >= 0.10:
            voltage_status = "critical"
        elif dev >= 0.05:
            voltage_status = "high"
        elif dev <= -0.05:
            voltage_status = "low"
    fdev = (payload.frequency_hz - 60.0) / 60.0
    frequency_status = "critical" if abs(fdev) >= 0.02 else ("high" if fdev >= 0.01 else ("low" if fdev <= -0.01 else "normal"))

    measurement_id = db.execute(text("""
        INSERT INTO power_grid.grid_measurements (
            node_id, measured_at, voltage_v, current_a, frequency_hz, active_power_kw,
            reactive_power_kvar, apparent_power_kva, power_factor, voltage_status, frequency_status
        ) VALUES (
            :node_id, :measured_at, :voltage_v, :current_a, :frequency_hz, :active_power_kw,
            :reactive_power_kvar, :apparent_power_kva, :power_factor, :voltage_status, :frequency_status
        )
        RETURNING measurement_id
    """), {
        "node_id": node["node_id"],
        "measured_at": payload.recorded_at or datetime.now(timezone.utc),
        "voltage_v": payload.voltage_v,
        "current_a": payload.current_a,
        "frequency_hz": payload.frequency_hz,
        "active_power_kw": payload.real_power_kw,
        "reactive_power_kvar": reactive,
        "apparent_power_kva": apparent,
        "power_factor": payload.power_factor,
        "voltage_status": voltage_status,
        "frequency_status": frequency_status,
    }).scalar_one()

    db.execute(text("""
        UPDATE power_grid.load_centers
        SET current_demand_kw = CASE
            WHEN totals.rated_total > 0 THEN :power_kw * (power_grid.load_centers.rated_demand_kw / totals.rated_total)
            ELSE power_grid.load_centers.current_demand_kw
        END, updated_at = :updated_at
        FROM (
            SELECT node_id, SUM(rated_demand_kw) AS rated_total
            FROM power_grid.load_centers
            WHERE node_id = :node_id
            GROUP BY node_id
        ) totals
        WHERE power_grid.load_centers.node_id = totals.node_id
    """), {
        "power_kw": payload.real_power_kw,
        "updated_at": datetime.now(timezone.utc),
        "node_id": node["node_id"],
    })

    if payload.fault_code:
        now = payload.recorded_at or datetime.now(timezone.utc)
        event_code = f"INGEST-{node['node_code']}-{now.strftime('%Y%m%d%H%M%S%f')}"[:75]
        db.execute(text("""
            INSERT INTO power_grid.grid_events (
                event_code, node_id, event_type, severity, event_status,
                event_message, detected_at, source_system
            ) VALUES (
                :event_code, :node_id, :event_type, 'high', 'open',
                :event_message, :detected_at, :source_system
            )
        """), {
            "event_code": event_code,
            "node_id": node["node_id"],
            "event_type": payload.fault_code,
            "event_message": f"Telemetry source reported {payload.fault_code} for {payload.asset_code}.",
            "detected_at": now,
            "source_system": payload.source or "Power Grid Sun",
        })

    db.commit()
    return {"measurement_id": str(measurement_id), "status": "accepted"}

@router.post("/simulation/tick", dependencies=[Depends(require_key)])
def simulation_tick(payload: SimulationTickRequest, db: Session = Depends(get_db)):
    rows = run_tick(db, payload.minutes, payload.fault_probability)
    moon = forward_tick(rows, payload.minutes)
    return {
        "inserted": len(rows),
        "data_moon": moon,
        "snapshot": current_snapshot(db),
    }

@router.get("/integrations/data-moon/status")
def data_moon_status():
    return data_moon_health()

@router.post("/forecasts")
def forecast(payload: ForecastRequest, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    params = {"since": since}
    scope_filter = ""
    if payload.scope != "CAMPUS":
        scope_filter = "AND (gn.node_code = :scope OR lc.load_code = :scope)"
        params["scope"] = payload.scope

    rows = db.execute(text(f"""
        SELECT gm.measured_at AS recorded_at, gm.active_power_kw AS real_power_kw
        FROM power_grid.grid_measurements gm
        JOIN power_grid.grid_nodes gn ON gn.node_id = gm.node_id
        LEFT JOIN power_grid.load_centers lc ON lc.node_id = gn.node_id
        WHERE gm.measured_at >= :since {scope_filter}
        ORDER BY gm.measured_at
    """), params).mappings().all()
    df = pd.DataFrame([{
        "recorded_at": r["recorded_at"],
        "real_power_kw": float(r["real_power_kw"] or 0),
    } for r in rows])
    if payload.scope == "CAMPUS" and not df.empty:
        df = df.groupby("recorded_at", as_index=False)["real_power_kw"].sum()

    result = train_and_predict(df, payload.horizon_minutes)
    if payload.scope == "CAMPUS":
        limit = 1500.0
    else:
        limit_row = db.execute(text("""
            SELECT COALESCE(SUM(lc.rated_demand_kw), 0) AS rated_kw
            FROM power_grid.grid_nodes gn
            LEFT JOIN power_grid.load_centers lc ON lc.node_id = gn.node_id
            WHERE gn.node_code = :scope OR lc.load_code = :scope
        """), {"scope": payload.scope}).mappings().one()
        limit = max(float(limit_row["rated_kw"] or 0) * 1.15, 100.0)
    probability = min(1.0, max(0.0, (result["upper"] - limit * .8) / (limit * .25)))
    return {**result, "scope": payload.scope, "horizon_minutes": payload.horizon_minutes,
            "overload_probability": probability, "limit_kw": limit}

@router.post("/diagnostics")
def request_diagnostic(
    payload: DiagnosticIn,
    db: Session = Depends(get_db)
):

    # Look up the requested asset from the canonical
    # Power Grid snapshot rather than the obsolete core.assets model.
    snapshot = current_snapshot(db)

    asset = next(
        (
            item
            for item in snapshot["assets"]
            if item["code"] == payload.asset_code
        ),
        None,
    )

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Power Grid asset not found."
        )

    rc_payload = {
        "source": "EES Power Grid Sun",
        "asset": asset["name"],
        "scenario": (
            f"Power Grid diagnostic request — "
            f"{payload.diagnostic_type}"
        ),
        "entities": {
            "asset_code": asset["code"],
            "voltage_v": asset["voltage_v"],
            "current_a": asset["current_a"],
            "instant_power_w": (
                asset["real_power_kw"] * 1000
            ),
            "power_factor": asset["power_factor"],
            "frequency_hz": asset["frequency_hz"],
            "health_percent": asset["health_pct"],
            "fault": asset["fault_code"] or "none",
            "diagnostic": "REQUESTED",
            "anomaly_count": (
                1 if asset["fault_code"] else 0
            ),
            "source_system": "EES Power Grid Sun",
        },
    }

    try:
        response = httpx.post(
            (
                settings.rc_controls_api_url
                + "/api/v1/rc/results"
            ),
            json=rc_payload,
            timeout=10.0,
        )

        response.raise_for_status()

        rc_result = response.json()

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "RC Controls API unavailable: "
                f"{exc}"
            ),
        )

    return {
        "status": "forwarded",
        "asset_code": asset["code"],
        "operating_snapshot": asset,
        "rc_controls": rc_result,
    }