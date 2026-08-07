from sqlalchemy import text
from app.db.session import engine, SessionLocal, Base
from app.models.entities import Facility, Asset

FACILITIES = [
    ("PHARMA","Pharma Manufacturing Plant","MANUFACTURING"),
    ("LOGISTICS","Global Supply Logistics Facility","LOGISTICS"),
    ("UTILITIES","Central Utilities Plant","UTILITIES"),
    ("EXEC","EES Executive Suites","ADMINISTRATION")]
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

def main():
    schemas = ["core","power_grid","pharma_process","supply_nexus","rc_controls","analytics","executive","audit"]
    with engine.begin() as c:
        for s in schemas: c.execute(text(f"CREATE SCHEMA IF NOT EXISTS {s}"))
    Base.metadata.create_all(engine)
    db=SessionLocal()
    try:
        if db.query(Facility).count()==0:
            facilities={}
            for code,name,kind in FACILITIES:
                f=Facility(code=code,name=name,facility_type=kind); db.add(f); db.flush(); facilities[code]=f
            for fac,code,name,area,typ,v,ph,kw,a,pf,eff,critical,cv in ASSETS:
                db.add(Asset(facility_id=facilities[fac].facility_id,code=code,name=name,area=area,asset_type=typ,
                    voltage_v=v,phases=ph,rated_power_kw=kw,rated_current_a=a,power_factor_nominal=pf,
                    efficiency_nominal=eff,critical=critical,metadata_json={"control_voltage_v":cv}))
            db.commit()
            print("Seeded EES industrial campus assets.")
        else: print("Seed data already present.")
    finally: db.close()

if __name__ == "__main__": main()
