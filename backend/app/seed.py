from sqlalchemy import text
from app.db.session import engine

FACILITIES = {
    "PHARMA": "Pharma Manufacturing Plant",
    "LOGISTICS": "Global Supply Logistics Facility",
    "UTILITIES": "Central Utilities Plant",
    "EXEC": "EES Executive Suites",
}

# facility, code, name, area, type, voltage, phases, rated_kw, rated_current,
# nominal_pf, efficiency, critical, control_voltage
ASSETS = [
("PHARMA","MIX-101","Bulk Mixing Tank Agitator","Liquid Processing","motor",480,3,37,52,0.88,0.91,True,24),
("PHARMA","PUMP-112","Transfer Pump","Liquid Processing","motor",480,3,15,23,0.86,0.88,False,24),
("PHARMA","TAB-201","Tablet Press","Solid Dose","motor",480,3,45,68,0.91,0.92,True,24),
("PHARMA","FILL-301","Bottle Filling Line","Packaging","motor",480,3,28,44,0.90,0.90,True,24),
("PHARMA","PKG-310","Case Packer and Conveyor","Packaging","motor",480,3,32,49,0.89,0.89,False,24),
("PHARMA","AHU-P1","Manufacturing Air Handler","HVAC","hvac",480,3,75,108,0.89,0.91,True,24),
("LOGISTICS","CONV-401","Main Sortation Conveyor","Sortation","motor",480,3,55,82,0.88,0.90,True,24),
("LOGISTICS","ASRS-410","ASRS Crane System","Automated Storage","motor",480,3,42,65,0.86,0.88,True,24),
("LOGISTICS","AMR-CHG","AMR Charging Bank","Fleet Charging","charger",480,3,80,110,0.96,0.94,False,24),
("LOGISTICS","FORK-CHG","Forklift Charger Bank","Fleet Charging","charger",480,3,96,130,0.95,0.93,False,24),
("LOGISTICS","COLD-420","Cold Storage Compressors","Cold Storage","compressor",480,3,120,172,0.87,0.90,True,24),
("UTILITIES","CH-01","Process Chiller 1","Chilled Water","chiller",4160,3,310,47,0.91,0.93,True,24),
("UTILITIES","AC-01","Plant Air Compressor 1","Compressed Air","compressor",480,3,185,260,0.89,0.92,True,24),
("UTILITIES","CT-01","Cooling Tower Fans","Cooling Water","motor",480,3,60,90,0.87,0.89,False,24),
("UTILITIES","RO-01","RO High Pressure Pump","Water Systems","motor",480,3,52,78,0.90,0.91,True,24),
("UTILITIES","CIP-01","CIP Supply and Return Pumps","CIP","motor",480,3,44,66,0.88,0.90,True,24),
("UTILITIES","BLR-01","Boiler Feedwater System","Steam","motor",480,3,70,103,0.89,0.91,True,24),
("EXEC","EOC-HVAC","Executive Operations HVAC","Executive Center","hvac",480,3,38,58,0.90,0.91,False,24),
("EXEC","EOC-IT","Executive Data and Visualization Systems","Executive Center","electronics",208,3,24,72,0.98,0.95,True,48),
]

DDL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS power_grid;

CREATE TABLE IF NOT EXISTS power_grid.grid_nodes (
    node_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    node_code varchar(50) NOT NULL UNIQUE,
    node_name varchar(150) NOT NULL,
    node_type varchar(50) NOT NULL,
    nominal_voltage_v numeric(12,3) NOT NULL,
    phase_configuration varchar(30) NOT NULL DEFAULT '3-phase',
    location_name varchar(150),
    operational_status varchar(30) NOT NULL DEFAULT 'online',
    criticality varchar(30) NOT NULL DEFAULT 'normal',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS power_grid.load_centers (
    load_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    load_code varchar(50) NOT NULL UNIQUE,
    load_name varchar(150) NOT NULL,
    node_id uuid NOT NULL,
    load_category varchar(50) NOT NULL,
    rated_demand_kw numeric(12,3) NOT NULL,
    current_demand_kw numeric(12,3) NOT NULL DEFAULT 0,
    priority_level integer NOT NULL DEFAULT 3,
    shed_enabled boolean NOT NULL DEFAULT false,
    operational_status varchar(30) NOT NULL DEFAULT 'online',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS power_grid.grid_measurements (
    measurement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id uuid NOT NULL,
    measured_at timestamptz NOT NULL DEFAULT now(),
    voltage_v numeric(12,3),
    current_a numeric(12,3),
    frequency_hz numeric(8,4),
    active_power_kw numeric(12,3),
    reactive_power_kvar numeric(12,3),
    apparent_power_kva numeric(12,3),
    power_factor numeric(6,4),
    voltage_status varchar(30) NOT NULL DEFAULT 'normal',
    frequency_status varchar(30) NOT NULL DEFAULT 'normal'
);
CREATE INDEX IF NOT EXISTS idx_grid_measurements_node_time
    ON power_grid.grid_measurements (node_id, measured_at DESC);

CREATE TABLE IF NOT EXISTS power_grid.grid_events (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_code varchar(75) NOT NULL,
    node_id uuid,
    event_type varchar(50) NOT NULL,
    severity varchar(30) NOT NULL,
    event_status varchar(30) NOT NULL DEFAULT 'open',
    event_message text NOT NULL,
    detected_at timestamptz NOT NULL DEFAULT now(),
    acknowledged_at timestamptz,
    cleared_at timestamptz,
    acknowledged_by varchar(150),
    source_system varchar(100) NOT NULL DEFAULT 'Power Grid Sun',
    created_at timestamptz NOT NULL DEFAULT now()
);
"""


def main():
    with engine.begin() as conn:
        # Execute statements individually for compatibility with psycopg/SQLAlchemy.
        for statement in [s.strip() for s in DDL.split(";") if s.strip()]:
            conn.execute(text(statement))

        count = conn.execute(text("SELECT COUNT(*) FROM power_grid.grid_nodes")).scalar_one()
        if count:
            print(f"Canonical Power Grid schema ready; {count} existing nodes preserved.")
            return

        for fac, code, name, area, typ, voltage, phases, rated_kw, _rated_current, _pf, _eff, critical, _cv in ASSETS:
            node_id = conn.execute(text("""
                INSERT INTO power_grid.grid_nodes (
                    node_code, node_name, node_type, nominal_voltage_v,
                    phase_configuration, location_name, operational_status, criticality
                ) VALUES (
                    :code, :name, :node_type, :voltage,
                    :phases, :location, 'online', :criticality
                ) RETURNING node_id
            """), {
                "code": code,
                "name": name,
                "node_type": typ,
                "voltage": voltage,
                "phases": f"{phases}-phase",
                "location": FACILITIES.get(fac, fac),
                "criticality": "critical" if critical else "normal",
            }).scalar_one()

            conn.execute(text("""
                INSERT INTO power_grid.load_centers (
                    load_code, load_name, node_id, load_category,
                    rated_demand_kw, current_demand_kw, priority_level,
                    shed_enabled, operational_status
                ) VALUES (
                    :load_code, :load_name, :node_id, :category,
                    :rated_kw, :current_kw, :priority,
                    :shed_enabled, 'online'
                )
            """), {
                "load_code": f"{code}-LOAD"[:50],
                "load_name": f"{name} Load",
                "node_id": node_id,
                "category": area[:50],
                "rated_kw": rated_kw,
                "current_kw": rated_kw * 0.72,
                "priority": 1 if critical else 3,
                "shed_enabled": not critical,
            })

        print(f"Seeded {len(ASSETS)} canonical Power Grid nodes and load centers.")


if __name__ == "__main__":
    main()
