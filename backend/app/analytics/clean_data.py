import re
import pandas as pd

def clean_telemetry_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["asset_code"] = df["asset_code"].astype(str).str.upper().str.replace(r"\s+", "-", regex=True)
    for col in ["voltage", "current", "pf", "temp_c"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.extract(r"([-+]?[0-9]*\.?[0-9]+)")[0], errors="coerce")
    df = df.drop_duplicates().dropna(subset=["timestamp", "asset_code"])
    df["voltage"] = df.groupby("asset_code")["voltage"].transform(lambda s: s.interpolate().ffill().bfill())
    df["state"] = df["state"].astype(str).str.upper().str.strip()
    return df.sort_values("timestamp").reset_index(drop=True)
