from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.entities import Asset, Facility, ElectricalTelemetry, Alert

def current_snapshot(db: Session) -> dict:
    latest_subq = (select(ElectricalTelemetry.asset_id, func.max(ElectricalTelemetry.recorded_at).label("max_time"))
                   .group_by(ElectricalTelemetry.asset_id).subquery())
    rows = (db.query(ElectricalTelemetry, Asset, Facility)
            .join(latest_subq, (ElectricalTelemetry.asset_id == latest_subq.c.asset_id) & (ElectricalTelemetry.recorded_at == latest_subq.c.max_time))
            .join(Asset, Asset.asset_id == ElectricalTelemetry.asset_id)
            .join(Facility, Facility.facility_id == Asset.facility_id).all())
    assets = []
    facilities: dict[str, dict] = {}
    total_kw = total_kvar = total_kva = 0.0
    for t, a, f in rows:
        item = {"asset_id": str(a.asset_id), "code": a.code, "name": a.name, "facility": f.code,
                "facility_name": f.name, "area": a.area, "asset_type": a.asset_type,
                "critical": a.critical, "operating_state": t.operating_state,
                "voltage_v": round(t.voltage_v,2), "current_a": round(t.current_a,2),
                "real_power_kw": round(t.real_power_kw,2), "reactive_power_kvar": round(t.reactive_power_kvar,2),
                "apparent_power_kva": round(t.apparent_power_kva,2), "power_factor": round(t.power_factor,3),
                "frequency_hz": round(t.frequency_hz,3), "breaker_utilization_pct": round(t.breaker_utilization_pct,1),
                "temperature_c": round(t.equipment_temperature_c,1), "health_pct": round(t.health_pct,1), "fault_code": t.fault_code}
        assets.append(item)
        agg = facilities.setdefault(f.code, {"code": f.code, "name": f.name, "real_power_kw": 0, "assets_running": 0, "faults": 0})
        agg["real_power_kw"] += t.real_power_kw
        agg["assets_running"] += int(t.operating_state == "RUNNING")
        agg["faults"] += int(bool(t.fault_code))
        total_kw += t.real_power_kw; total_kvar += t.reactive_power_kvar; total_kva += t.apparent_power_kva
    campus_pf = total_kw / total_kva if total_kva else 1.0
    alerts = db.query(Alert).filter(Alert.status == "OPEN").order_by(Alert.created_at.desc()).limit(12).all()
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "campus": {"real_power_kw": round(total_kw,2),
            "reactive_power_kvar": round(total_kvar,2), "apparent_power_kva": round(total_kva,2),
            "power_factor": round(campus_pf,3), "open_alerts": len(alerts)},
            "facilities": [{**v, "real_power_kw": round(v["real_power_kw"],2)} for v in facilities.values()],
            "assets": assets, "alerts": [{"severity": x.severity, "asset_code": x.asset_code, "title": x.title,
            "message": x.message, "created_at": x.created_at.isoformat()} for x in alerts]}
