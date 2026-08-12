from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class GridNode(Base):
    __tablename__ = "grid_nodes"
    __table_args__ = {"schema": "power_grid"}

    node_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    node_code: Mapped[str] = mapped_column(String(50), unique=True)
    node_name: Mapped[str] = mapped_column(String(150))
    node_type: Mapped[str] = mapped_column(String(50))
    nominal_voltage_v: Mapped[float] = mapped_column(Numeric(12, 3))
    phase_configuration: Mapped[str] = mapped_column(String(30), default="3-phase")
    location_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    operational_status: Mapped[str] = mapped_column(String(30), default="online")
    criticality: Mapped[str] = mapped_column(String(30), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class LoadCenter(Base):
    __tablename__ = "load_centers"
    __table_args__ = {"schema": "power_grid"}

    load_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    load_code: Mapped[str] = mapped_column(String(50), unique=True)
    load_name: Mapped[str] = mapped_column(String(150))
    node_id: Mapped[UUID] = mapped_column()
    load_category: Mapped[str] = mapped_column(String(50))
    rated_demand_kw: Mapped[float] = mapped_column(Numeric(12, 3))
    current_demand_kw: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    priority_level: Mapped[int] = mapped_column(Integer, default=3)
    shed_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    operational_status: Mapped[str] = mapped_column(String(30), default="online")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GridMeasurement(Base):
    __tablename__ = "grid_measurements"
    __table_args__ = {"schema": "power_grid"}

    measurement_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    node_id: Mapped[UUID] = mapped_column()
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    voltage_v: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    current_a: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    frequency_hz: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    active_power_kw: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    reactive_power_kvar: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    apparent_power_kva: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    power_factor: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    voltage_status: Mapped[str] = mapped_column(String(30), default="normal")
    frequency_status: Mapped[str] = mapped_column(String(30), default="normal")


class GridEvent(Base):
    __tablename__ = "grid_events"
    __table_args__ = {"schema": "power_grid"}

    event_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_code: Mapped[str] = mapped_column(String(75))
    node_id: Mapped[UUID | None] = mapped_column(nullable=True)
    event_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(30))
    event_status: Mapped[str] = mapped_column(String(30), default="open")
    event_message: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_system: Mapped[str] = mapped_column(String(100), default="Power Grid Sun")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
