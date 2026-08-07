from __future__ import annotations
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy().sort_values("recorded_at")
    x["recorded_at"] = pd.to_datetime(x["recorded_at"], utc=True)
    x["hour"] = x["recorded_at"].dt.hour
    x["dayofweek"] = x["recorded_at"].dt.dayofweek
    x["hour_sin"] = np.sin(2 * np.pi * x["hour"] / 24)
    x["hour_cos"] = np.cos(2 * np.pi * x["hour"] / 24)
    for lag in (1, 2, 3, 6, 12):
        x[f"lag_{lag}"] = x["real_power_kw"].shift(lag)
    x["rolling_mean_6"] = x["real_power_kw"].rolling(6, min_periods=1).mean()
    x["rolling_std_6"] = x["real_power_kw"].rolling(6, min_periods=2).std().fillna(0)
    return x.dropna()

def train_and_predict(df: pd.DataFrame, horizon_minutes: int = 15) -> dict:
    features = build_features(df)
    if len(features) < 24:
        current = float(df["real_power_kw"].tail(6).mean()) if len(df) else 0.0
        return {"prediction": current, "lower": current * .90, "upper": current * 1.12,
                "mae": None, "model": "rolling-baseline"}
    cols = ["hour_sin", "hour_cos", "dayofweek", "lag_1", "lag_2", "lag_3", "lag_6", "lag_12", "rolling_mean_6", "rolling_std_6"]
    X, y = features[cols], features["real_power_kw"]
    model = HistGradientBoostingRegressor(max_depth=5, learning_rate=.08, random_state=42)
    split = TimeSeriesSplit(n_splits=min(4, max(2, len(X)//20)))
    errors = []
    for train_idx, test_idx in split.split(X):
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        errors.append(mean_absolute_error(y.iloc[test_idx], model.predict(X.iloc[test_idx])))
    model.fit(X, y)
    pred = float(model.predict(X.tail(1))[0])
    mae = float(np.mean(errors)) if errors else pred * .08
    return {"prediction": max(0, pred), "lower": max(0, pred - 1.64*mae), "upper": pred + 1.64*mae,
            "mae": mae, "model": "HistGradientBoostingRegressor"}
