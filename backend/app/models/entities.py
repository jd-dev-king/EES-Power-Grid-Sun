from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Float, DateTime, ForeignKey, Integer, Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Facility(Base):
    __tablename__ = "facilities"
    __table_args__ = {"schema": "core"}
    facility_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    facility_type: Mapped[str] = mapped_column(String(40))
    assets: Mapped[list[Asset]] = relationship(back_populates="facility")

class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = {"schema": "core"}
    asset_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("core.facilities.facility_id"), index=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    area: Mapped[str] = mapped_column(String(80))
    asset_type: Mapped[str] = mapped_column(String(60))
    voltage_v: Mapped[float] = mapped_column(Float)
    phases: Mapped[int] = mapped_column(Integer, default=3)
    rated_power_kw: Mapped[float] = mapped_column(Float)
    rated_current_a: Mapped[float] = mapped_column(Float)
    power_factor_nominal: Mapped[float] = mapped_column(Float, default=0.9)
    efficiency_nominal: Mapped[float] = mapped_column(Float, default=0.9)
    critical: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    facility: Mapped[Facility] = relationship(back_populates="assets")

class ElectricalTelemetry(Base):
    __tablename__ = "electrical_telemetry"
    __table_args__ = {"schema": "power_grid"}
    telemetry_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("core.assets.asset_id"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    operating_state: Mapped[str] = mapped_column(String(40))
    voltage_v: Mapped[float] = mapped_column(Float)
    current_a: Mapped[float] = mapped_column(Float)
    real_power_kw: Mapped[float] = mapped_column(Float)
    reactive_power_kvar: Mapped[float] = mapped_column(Float)
    apparent_power_kva: Mapped[float] = mapped_column(Float)
    power_factor: Mapped[float] = mapped_column(Float)
    frequency_hz: Mapped[float] = mapped_column(Float)
    energy_kwh: Mapped[float] = mapped_column(Float, default=0)
    breaker_utilization_pct: Mapped[float] = mapped_column(Float)
    equipment_temperature_c: Mapped[float] = mapped_column(Float)
    health_pct: Mapped[float] = mapped_column(Float, default=100)
    fault_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="SIMULATION")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

class Forecast(Base):
    __tablename__ = "predictions"
    __table_args__ = {"schema": "analytics"}
    prediction_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    target_scope: Mapped[str] = mapped_column(String(100), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    horizon_minutes: Mapped[int] = mapped_column(Integer)
    predicted_power_kw: Mapped[float] = mapped_column(Float)
    lower_bound_kw: Mapped[float] = mapped_column(Float)
    upper_bound_kw: Mapped[float] = mapped_column(Float)
    overload_probability: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(100))
    features_json: Mapped[dict] = mapped_column(JSON, default=dict)

class Alert(Base):
    __tablename__ = "executive_alerts"
    __table_args__ = {"schema": "executive"}
    alert_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    severity: Mapped[str] = mapped_column(String(20))
    source_twin: Mapped[str] = mapped_column(String(50))
    asset_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

class DiagnosticRequest(Base):
    __tablename__ = "diagnostic_requests"
    __table_args__ = {"schema": "rc_controls"}
    request_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    source_asset_id: Mapped[UUID] = mapped_column(ForeignKey("core.assets.asset_id"))
    requested_by_twin: Mapped[str] = mapped_column(String(50), default="POWER_GRID_SUN")
    diagnostic_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    operating_snapshot: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
