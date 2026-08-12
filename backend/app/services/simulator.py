from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
import random
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _schedule_factor(location: str | None, node_type: str | None, hour: int) -> float:
    label = f"{location or ''} {node_type or ''}".lower()
    if "pharma" in label or "manufact" in label:
        shift = 1.0 if 6 <= hour < 22 else 0.58
    elif "logistics" in label or "warehouse" in label:
        shift = 1.0 if 5 <= hour < 23 else 0.44
    else:
        shift = 0.92 if 6 <= hour < 22 else 0.70
    return shift * (0.82 + 0.18 * random.random())


def _status(value: float, nominal: float, warn_pct: float, critical_pct: float) -> str:
    if nominal <= 0:
        return "normal"
    deviation = (value - nominal) / nominal
    if abs(deviation) >= critical_pct:
        return "critical"
    if deviation >= warn_pct:
        return "high"
    if deviation <= -warn_pct:
        return "low"
    return "normal"


def run_tick(db: Session, minutes: float = 1, fault_probability: float = 0.003) -> list[dict[str, Any]]:
    """Generate one canonical grid measurement per Power Grid node.

    The live EES database uses power_grid.grid_nodes/load_centers/grid_measurements.
    Simulation therefore writes directly to those canonical objects; no core.assets
    or power_grid.electrical_telemetry compatibility schema is required.
    """
    nodes = db.execute(text("""
        SELECT
            gn.node_id,
            gn.node_code,
            gn.node_name,
            gn.node_type,
            gn.nominal_voltage_v,
            gn.phase_configuration,
            gn.location_name,
            gn.operational_status,
            gn.criticality,
            COALESCE(SUM(lc.rated_demand_kw), 0) AS rated_demand_kw,
            COALESCE(SUM(lc.current_demand_kw), 0) AS current_demand_kw
        FROM power_grid.grid_nodes gn
        LEFT JOIN power_grid.load_centers lc ON lc.node_id = gn.node_id
        GROUP BY gn.node_id
        ORDER BY gn.node_code
    """)).mappings().all()

    if not nodes:
        return []

    now = datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []

    for node in nodes:
        nominal_v = float(node["nominal_voltage_v"] or 0)
        rated_kw = float(node["rated_demand_kw"] or 0)
        current_kw = float(node["current_demand_kw"] or 0)
        factor = _schedule_factor(node["location_name"], node["node_type"], now.hour)

        # Use configured load-center demand as the operating baseline when present,
        # otherwise derive a conservative baseline from rated demand.
        baseline_kw = current_kw if current_kw > 0 else rated_kw * factor
        if baseline_kw <= 0:
            baseline_kw = 0.0
        power_kw = baseline_kw * (0.96 + 0.08 * random.random())
        if rated_kw > 0:
            power_kw = min(power_kw, rated_kw * 1.10)

        pf = max(0.72, min(0.995, 0.92 + random.gauss(0, 0.018)))
        voltage = nominal_v * (1 + random.gauss(0, 0.006)) if nominal_v else 0.0
        frequency = 60.0 + random.gauss(0, 0.018)
        fault_code = None
        severity = None

        if random.random() < fault_probability:
            fault_code = random.choice(["VOLTAGE_SAG", "VOLTAGE_SWELL", "FREQUENCY_DRIFT", "OVERLOAD"])
            if fault_code == "VOLTAGE_SAG":
                voltage = nominal_v * random.uniform(0.86, 0.92)
                severity = "high"
            elif fault_code == "VOLTAGE_SWELL":
                voltage = nominal_v * random.uniform(1.08, 1.13)
                severity = "high"
            elif fault_code == "FREQUENCY_DRIFT":
                frequency = random.choice([random.uniform(58.8, 59.3), random.uniform(60.7, 61.2)])
                severity = "high"
            else:
                power_kw = rated_kw * random.uniform(1.03, 1.10) if rated_kw else power_kw * 1.15
                pf = max(0.72, pf - 0.06)
                severity = "critical"

        apparent_kva = power_kw / max(pf, 0.1)
        reactive_kvar = sqrt(max(apparent_kva ** 2 - power_kw ** 2, 0.0))
        phases = str(node["phase_configuration"] or "3-phase").lower()
        if voltage > 0:
            if phases.startswith("3"):
                current_a = apparent_kva * 1000 / (sqrt(3) * voltage)
            else:
                current_a = apparent_kva * 1000 / voltage
        else:
            current_a = 0.0

        voltage_status = _status(voltage, nominal_v, 0.05, 0.10)
        frequency_status = _status(frequency, 60.0, 0.01, 0.02)

        inserted = db.execute(text("""
            INSERT INTO power_grid.grid_measurements (
                node_id, measured_at, voltage_v, current_a, frequency_hz,
                active_power_kw, reactive_power_kvar, apparent_power_kva,
                power_factor, voltage_status, frequency_status
            ) VALUES (
                :node_id, :measured_at, :voltage_v, :current_a, :frequency_hz,
                :active_power_kw, :reactive_power_kvar, :apparent_power_kva,
                :power_factor, :voltage_status, :frequency_status
            )
            RETURNING measurement_id
        """), {
            "node_id": node["node_id"],
            "measured_at": now,
            "voltage_v": voltage,
            "current_a": current_a,
            "frequency_hz": frequency,
            "active_power_kw": power_kw,
            "reactive_power_kvar": reactive_kvar,
            "apparent_power_kva": apparent_kva,
            "power_factor": pf,
            "voltage_status": voltage_status,
            "frequency_status": frequency_status,
        }).scalar_one()

        # Keep load-center current demand aligned with the measurement. Multiple
        # load centers on a node share the simulated node demand proportionally.
        if rated_kw > 0:
            db.execute(text("""
                UPDATE power_grid.load_centers
                SET current_demand_kw = :node_power_kw * (rated_demand_kw / :rated_total),
                    updated_at = :updated_at
                WHERE node_id = :node_id
            """), {
                "node_power_kw": power_kw,
                "rated_total": rated_kw,
                "updated_at": now,
                "node_id": node["node_id"],
            })

        if fault_code:
            event_code = f"SIM-{node['node_code']}-{now.strftime('%Y%m%d%H%M%S%f')}"[:75]
            db.execute(text("""
                INSERT INTO power_grid.grid_events (
                    event_code, node_id, event_type, severity, event_status,
                    event_message, detected_at, source_system
                ) VALUES (
                    :event_code, :node_id, :event_type, :severity, 'open',
                    :event_message, :detected_at, 'Power Grid Sun'
                )
            """), {
                "event_code": event_code,
                "node_id": node["node_id"],
                "event_type": "fault",
                "severity": severity or "high",
                "event_message": (
                    f"Simulation detected {fault_code.replace('_', ' ').lower()} "
                    f"at {node['node_name']}."
                ),

                "detected_at": now,
            })

        records.append({
            "measurement_id": str(inserted),
            "node_id": str(node["node_id"]),
            "asset_id": str(node["node_id"]),
            "asset_code": node["node_code"],
            "asset_name": node["node_name"],
            "facility_code": node["location_name"] or "EES Campus",
            "facility_name": node["location_name"] or "EES Campus",
            "area": node["location_name"] or "EES Campus",
            "asset_type": node["node_type"],
            "recorded_at": now.isoformat(),
            "operating_state": str(node["operational_status"] or "online").upper(),
            "voltage_v": round(voltage, 3),
            "current_a": round(current_a, 3),
            "real_power_kw": round(power_kw, 3),
            "reactive_power_kvar": round(reactive_kvar, 3),
            "apparent_power_kva": round(apparent_kva, 3),
            "power_factor": round(pf, 4),
            "frequency_hz": round(frequency, 4),
            "energy_kwh": round(power_kw * minutes / 60.0, 4),
            "breaker_utilization_pct": round((power_kw / rated_kw) * 100, 2) if rated_kw else 0.0,
            "equipment_temperature_c": None,
            "health_pct": 72.0 if fault_code else 100.0,
            "fault_code": fault_code,
            "source": "SIMULATION",
            "voltage_status": voltage_status,
            "frequency_status": frequency_status,
        })

    db.commit()
    return records
