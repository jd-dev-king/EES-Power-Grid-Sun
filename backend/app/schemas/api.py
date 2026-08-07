from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class TelemetryIn(BaseModel):
    asset_code: str
    recorded_at: datetime | None = None
    operating_state: str
    voltage_v: float = Field(gt=0)
    current_a: float = Field(ge=0)
    real_power_kw: float = Field(ge=0)
    power_factor: float = Field(gt=0, le=1)
    frequency_hz: float = Field(default=60, ge=55, le=65)
    equipment_temperature_c: float = 25
    health_pct: float = Field(default=100, ge=0, le=100)
    fault_code: str | None = None
    source: str = "MATLAB"

class DiagnosticIn(BaseModel):
    asset_code: str
    diagnostic_type: str = "MOTOR_CONTROL_ANALYSIS"

class ForecastRequest(BaseModel):
    scope: str = "CAMPUS"
    horizon_minutes: int = Field(default=15, ge=5, le=1440)

class SimulationTickRequest(BaseModel):
    minutes: float = Field(default=1.0, gt=0, le=60)
    fault_probability: float = Field(default=0.003, ge=0, le=0.2)
