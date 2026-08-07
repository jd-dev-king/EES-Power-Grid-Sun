from datetime import datetime, timedelta, timezone
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import Asset, ElectricalTelemetry, Forecast, DiagnosticRequest
from app.schemas.api import TelemetryIn, DiagnosticIn, ForecastRequest, SimulationTickRequest
from app.services.power_math import three_phase_metrics, single_phase_metrics
from app.services.simulator import run_tick
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
    q = db.query(Asset)
    if facility:
        q = q.join(Asset.facility).filter_by(code=facility.upper())
    return [{"asset_id": str(a.asset_id), "code": a.code, "name": a.name, "area": a.area,
             "type": a.asset_type, "rated_power_kw": a.rated_power_kw, "voltage_v": a.voltage_v,
             "critical": a.critical} for a in q.order_by(Asset.code).all()]

@router.post("/power/telemetry", dependencies=[Depends(require_key)])
def ingest_telemetry(payload: TelemetryIn, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.code == payload.asset_code).one_or_none()
    if not asset: raise HTTPException(404, "Asset not found")
    metrics = three_phase_metrics(payload.voltage_v, payload.current_a, payload.power_factor, asset.efficiency_nominal) if asset.phases == 3 else single_phase_metrics(payload.voltage_v, payload.current_a, payload.power_factor)
    # Use supplied real power as source of truth, retain calculated apparent/reactive values.
    apparent = payload.real_power_kw / payload.power_factor
    reactive = max((apparent**2 - payload.real_power_kw**2), 0) ** .5
    row = ElectricalTelemetry(asset_id=asset.asset_id, recorded_at=payload.recorded_at or datetime.now(timezone.utc),
        operating_state=payload.operating_state, voltage_v=payload.voltage_v, current_a=payload.current_a,
        real_power_kw=payload.real_power_kw, reactive_power_kvar=reactive, apparent_power_kva=apparent,
        power_factor=payload.power_factor, frequency_hz=payload.frequency_hz,
        energy_kwh=0, breaker_utilization_pct=100*payload.current_a/max(asset.rated_current_a*1.25,1),
        equipment_temperature_c=payload.equipment_temperature_c, health_pct=payload.health_pct,
        fault_code=payload.fault_code, source=payload.source, metadata_json={"calculated": metrics})
    db.add(row); db.commit()
    return {"telemetry_id": str(row.telemetry_id), "status": "accepted"}

@router.post("/simulation/tick", dependencies=[Depends(require_key)])
def simulation_tick(payload: SimulationTickRequest, db: Session = Depends(get_db)):
    rows = run_tick(db, payload.minutes, payload.fault_probability)
    return {"inserted": len(rows), "snapshot": current_snapshot(db)}

@router.post("/forecasts")
def forecast(payload: ForecastRequest, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    q = db.query(ElectricalTelemetry).filter(ElectricalTelemetry.recorded_at >= since)
    if payload.scope != "CAMPUS":
        q = q.join(Asset).filter(Asset.code == payload.scope)
    rows = q.order_by(ElectricalTelemetry.recorded_at).all()
    if payload.scope == "CAMPUS":
        df = pd.DataFrame([{"recorded_at": r.recorded_at, "real_power_kw": r.real_power_kw} for r in rows])
        if not df.empty: df = df.groupby("recorded_at", as_index=False)["real_power_kw"].sum()
    else:
        df = pd.DataFrame([{"recorded_at": r.recorded_at, "real_power_kw": r.real_power_kw} for r in rows])
    result = train_and_predict(df, payload.horizon_minutes)
    limit = 1500 if payload.scope == "CAMPUS" else (db.query(Asset).filter(Asset.code == payload.scope).one_or_none().rated_power_kw * 1.15 if db.query(Asset).filter(Asset.code == payload.scope).one_or_none() else 100)
    probability = min(1.0, max(0.0, (result["upper"] - limit*.8)/(limit*.25)))
    record = Forecast(target_scope=payload.scope, horizon_minutes=payload.horizon_minutes,
        predicted_power_kw=result["prediction"], lower_bound_kw=result["lower"], upper_bound_kw=result["upper"],
        overload_probability=probability, model_name=result["model"], features_json={"mae": result["mae"]})
    db.add(record); db.commit()
    return {**result, "scope": payload.scope, "horizon_minutes": payload.horizon_minutes,
            "overload_probability": probability, "limit_kw": limit}

@router.post("/diagnostics", dependencies=[Depends(require_key)])
def request_diagnostic(payload: DiagnosticIn, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.code == payload.asset_code).one_or_none()
    if not asset: raise HTTPException(404, "Asset not found")
    latest = db.query(ElectricalTelemetry).filter(ElectricalTelemetry.asset_id == asset.asset_id).order_by(ElectricalTelemetry.recorded_at.desc()).first()
    if not latest: raise HTTPException(409, "No telemetry for asset")
    snapshot = {"asset_code": asset.code, "asset_name": asset.name, "voltage_v": latest.voltage_v,
        "current_a": latest.current_a, "real_power_kw": latest.real_power_kw, "power_factor": latest.power_factor,
        "frequency_hz": latest.frequency_hz, "temperature_c": latest.equipment_temperature_c,
        "health_pct": latest.health_pct, "fault_code": latest.fault_code, "control_voltage_v": asset.metadata_json.get("control_voltage_v",24)}
    req = DiagnosticRequest(source_asset_id=asset.asset_id, diagnostic_type=payload.diagnostic_type,
                            operating_snapshot=snapshot)
    db.add(req); db.commit()
    return {"request_id": str(req.request_id), "status": req.status, "operating_snapshot": snapshot}
