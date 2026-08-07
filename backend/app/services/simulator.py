from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
import random
from sqlalchemy.orm import Session
from app.models.entities import Asset, ElectricalTelemetry, Alert

FAULTS = {
    "motor": [("BEARING_FRICTION", 1.16, 0.88, 14), ("PHASE_IMBALANCE", 1.11, 0.82, 10), ("COOLING_BLOCKED", 1.08, 0.92, 18)],
    "compressor": [("AIR_LEAK", 1.20, 0.91, 16), ("FILTER_RESTRICTION", 1.13, 0.89, 12)],
    "chiller": [("FOULED_CONDENSER", 1.18, 0.90, 15), ("LOW_REFRIGERANT", 1.12, 0.86, 10)],
    "heater": [("ELEMENT_DEGRADATION", 0.62, 1.0, 6), ("RELAY_WELDED", 1.03, 1.0, 20)],
}

def _schedule_factor(asset: Asset, hour: int) -> float:
    facility = asset.facility.code
    if facility == "PHARMA":
        shift = 1.0 if 6 <= hour < 22 else 0.58
    elif facility == "LOGISTICS":
        shift = 1.0 if 5 <= hour < 23 else 0.44
    else:
        shift = 0.92 if 6 <= hour < 22 else 0.70
    cycle = 0.75 + 0.25 * random.random()
    if asset.asset_type in {"chiller", "compressor", "hvac"}: cycle = 0.70 + 0.30 * random.random()
    return shift * cycle

def simulate_asset(asset: Asset, minutes: float, fault_probability: float) -> ElectricalTelemetry:
    now = datetime.now(timezone.utc)
    factor = _schedule_factor(asset, now.hour)
    state = "RUNNING" if factor > 0.58 else "STANDBY"
    fault_code = None
    pf = max(0.68, min(0.99, asset.power_factor_nominal + random.gauss(0, 0.012)))
    efficiency = asset.efficiency_nominal
    temperature = 28 + factor * 31 + random.gauss(0, 1.3)
    power_kw = asset.rated_power_kw * factor
    health = 98 + random.gauss(0, 0.4)
    if random.random() < fault_probability:
        key = asset.asset_type if asset.asset_type in FAULTS else "motor"
        fault_code, multiplier, pf_mult, temp_add = random.choice(FAULTS[key])
        power_kw *= multiplier
        pf *= pf_mult
        temperature += temp_add
        health -= random.uniform(8, 24)
    voltage = asset.voltage_v * (1 + random.gauss(0, 0.006))
    if asset.phases == 3:
        current = power_kw * 1000 / (sqrt(3) * voltage * max(pf, 0.1))
    else:
        current = power_kw * 1000 / (voltage * max(pf, 0.1))
    apparent = power_kw / max(pf, 0.1)
    reactive = sqrt(max(apparent**2 - power_kw**2, 0))
    breaker_pct = 100 * current / max(asset.rated_current_a * 1.25, 1)
    return ElectricalTelemetry(
        asset_id=asset.asset_id, recorded_at=now, operating_state=state,
        voltage_v=voltage, current_a=current, real_power_kw=power_kw,
        reactive_power_kvar=reactive, apparent_power_kva=apparent,
        power_factor=pf, frequency_hz=60 + random.gauss(0, 0.018),
        energy_kwh=power_kw * minutes / 60, breaker_utilization_pct=breaker_pct,
        equipment_temperature_c=temperature, health_pct=max(0, min(100, health)),
        fault_code=fault_code, source="SIMULATION", metadata_json={"schedule_factor": factor}
    )

def run_tick(db: Session, minutes: float = 1, fault_probability: float = 0.003) -> list[ElectricalTelemetry]:
    assets = db.query(Asset).all()
    rows = [simulate_asset(a, minutes, fault_probability) for a in assets]
    db.add_all(rows)
    for row, asset in zip(rows, assets):
        severity = None
        title = None
        if row.fault_code:
            severity, title = "HIGH", f"{asset.name}: {row.fault_code.replace('_', ' ').title()}"
        elif row.breaker_utilization_pct >= 100:
            severity, title = "CRITICAL", f"Breaker overload risk: {asset.name}"
        elif row.equipment_temperature_c >= 82:
            severity, title = "HIGH", f"High equipment temperature: {asset.name}"
        if severity:
            db.add(Alert(severity=severity, source_twin="POWER_GRID_SUN", asset_code=asset.code,
                         title=title, message=f"Power {row.real_power_kw:.1f} kW; current {row.current_a:.1f} A; temperature {row.equipment_temperature_c:.1f} C.",
                         metadata_json={"fault_code": row.fault_code, "breaker_utilization_pct": row.breaker_utilization_pct}))
    db.commit()
    return rows
