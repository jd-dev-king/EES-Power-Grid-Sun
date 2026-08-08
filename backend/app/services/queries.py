from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def current_snapshot(db: Session) -> dict:

    rows = db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (gm.node_id)
                    gm.node_id,
                    gm.measured_at,
                    gm.voltage_v,
                    gm.current_a,
                    gm.frequency_hz,
                    gm.active_power_kw,
                    gm.reactive_power_kvar,
                    gm.apparent_power_kva,
                    gm.power_factor,
                    gm.voltage_status,
                    gm.frequency_status
                FROM power_grid.grid_measurements gm
                ORDER BY gm.node_id, gm.measured_at DESC
            )
            SELECT
                gn.node_id,
                gn.node_code,
                gn.node_name,
                gn.node_type,
                gn.location_name,
                gn.nominal_voltage_v,
                gn.operational_status,
                gn.criticality,

                l.measured_at,
                l.voltage_v,
                l.current_a,
                l.frequency_hz,
                l.active_power_kw,
                l.reactive_power_kvar,
                l.apparent_power_kva,
                l.power_factor,
                l.voltage_status,
                l.frequency_status,

                lc.load_code,
                lc.load_name,
                lc.load_category,
                lc.rated_demand_kw,
                lc.current_demand_kw,
                lc.operational_status AS load_status

            FROM power_grid.grid_nodes gn

            LEFT JOIN latest l
                ON l.node_id = gn.node_id

            LEFT JOIN power_grid.load_centers lc
                ON lc.node_id = gn.node_id

            ORDER BY gn.node_code;
            """
        )
    ).mappings().all()

    assets = []
    facilities = {}

    total_kw = 0.0
    total_kvar = 0.0
    total_kva = 0.0

    for row in rows:

        real_kw = float(row["active_power_kw"] or 0)
        reactive_kvar = float(row["reactive_power_kvar"] or 0)
        apparent_kva = float(row["apparent_power_kva"] or 0)

        voltage = float(
            row["voltage_v"]
            or row["nominal_voltage_v"]
            or 0
        )

        current = float(row["current_a"] or 0)
        frequency = float(row["frequency_hz"] or 0)
        power_factor = float(row["power_factor"] or 0)

        location = row["location_name"] or "EES Campus"

        fault = None

        if row["operational_status"] == "fault":
            fault = "NODE_FAULT"
        elif row["voltage_status"] in ("critical", "high", "low"):
            fault = f"VOLTAGE_{str(row['voltage_status']).upper()}"
        elif row["frequency_status"] in ("critical", "high", "low"):
            fault = f"FREQUENCY_{str(row['frequency_status']).upper()}"

        health = 100.0

        if row["operational_status"] == "fault":
            health = 40.0
        elif row["criticality"] == "critical":
            health = 70.0
        elif fault:
            health = 75.0

        rated_kw = float(row["rated_demand_kw"] or 0)

        breaker_utilization = (
            (real_kw / rated_kw) * 100
            if rated_kw > 0
            else 0
        )

        item = {
            "asset_id": str(row["node_id"]),
            "code": row["load_code"] or row["node_code"],
            "name": row["load_name"] or row["node_name"],
            "facility": location,
            "facility_name": location,
            "area": location,
            "asset_type": row["load_category"] or row["node_type"],
            "critical": row["criticality"] in ("high", "critical"),
            "operating_state": str(
                row["load_status"]
                or row["operational_status"]
            ).upper(),

            "voltage_v": round(voltage, 2),
            "current_a": round(current, 2),
            "real_power_kw": round(real_kw, 2),
            "reactive_power_kvar": round(reactive_kvar, 2),
            "apparent_power_kva": round(apparent_kva, 2),
            "power_factor": round(power_factor, 3),
            "frequency_hz": round(frequency, 3),

            "breaker_utilization_pct": round(
                breaker_utilization,
                1
            ),

            # Canonical schema currently has no equipment
            # temperature measurement.
            "temperature_c": None,

            "health_pct": health,
            "fault_code": fault,
        }

        assets.append(item)

        facility = facilities.setdefault(
            location,
            {
                "code": location,
                "name": location,
                "real_power_kw": 0.0,
                "assets_running": 0,
                "faults": 0,
            },
        )

        facility["real_power_kw"] += real_kw

        if row["operational_status"] == "online":
            facility["assets_running"] += 1

        if fault:
            facility["faults"] += 1

        total_kw += real_kw
        total_kvar += reactive_kvar
        total_kva += apparent_kva

    campus_pf = (
        total_kw / total_kva
        if total_kva
        else 1.0
    )

    alert_rows = db.execute(
        text(
            """
            SELECT
                ge.severity,
                gn.node_code,
                ge.event_type,
                ge.event_message,
                ge.detected_at
            FROM power_grid.grid_events ge
            LEFT JOIN power_grid.grid_nodes gn
                ON gn.node_id = ge.node_id
            WHERE ge.event_status = 'open'
            ORDER BY ge.detected_at DESC
            LIMIT 12;
            """
        )
    ).mappings().all()

    alerts = [
        {
            "severity": row["severity"],
            "asset_code": row["node_code"],
            "title": row["event_type"],
            "message": row["event_message"],
            "created_at": row["detected_at"].isoformat(),
        }
        for row in alert_rows
    ]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),

        "campus": {
            "real_power_kw": round(total_kw, 2),
            "reactive_power_kvar": round(total_kvar, 2),
            "apparent_power_kva": round(total_kva, 2),
            "power_factor": round(campus_pf, 3),
            "open_alerts": len(alerts),
        },

        "facilities": [
            {
                **facility,
                "real_power_kw": round(
                    facility["real_power_kw"],
                    2
                ),
            }
            for facility in facilities.values()
        ],

        "assets": assets,
        "alerts": alerts,
    }