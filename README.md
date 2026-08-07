# Power Grid Sun v4.0.0

**MATLAB–Python Industrial Power & Utilities Digital Twin for the EES Universe**

Power Grid Sun is the electrical and utilities backbone connecting the Pharma Process Twin, Global Supply Nexus, RC Controls Twin, and EES Executive Suites. PostgreSQL on Railway is the authoritative datastore. MATLAB/Simulink provides the engineering simulation layer, Python supplies data engineering and machine-learning services, and the Three.js client visualizes the industrial campus.

## Included in this foundation

- Railway-ready FastAPI service
- PostgreSQL schemas for all EES twins
- SQLAlchemy models and campus seed data
- Physics-based three-phase and single-phase power calculations
- Industrial equipment simulation with schedule factors, thermal behavior, power factor, breaker loading, energy, and realistic fault signatures
- PostgreSQL-backed diagnostic requests for RC Controls Twin
- pandas messy-CSV cleaning example
- scikit-learn time-series forecasting with lagged features and time-ordered validation
- MATLAB telemetry client, power calculations, forecasting client, and functional UI application class
- MATLAB script that builds the first Simulink campus model programmatically
- Three.js industrial campus client with live API polling and demo fallback

## Industrial story

1. **Power Grid Sun** supplies and monitors the industrial campus.
2. **Pharma Process Twin** consumes power to manufacture products.
3. **Global Supply Nexus** consumes power to store and move materials.
4. **RC Controls Twin** receives persisted diagnostic packets for motors, panels, VFDs, and control circuits.
5. **EES Executive Suites** displays campus-level operational, energy, maintenance, and risk intelligence.

## Local backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.seed
uvicorn app.main:app --reload
```

A PostgreSQL database must be available at `DATABASE_URL`.

Run a simulation tick:

```bash
curl -X POST http://localhost:8000/api/v1/simulation/tick \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me' \
  -d '{"minutes":1,"fault_probability":0.01}'
```

## Railway

1. Create a Railway project.
2. Add PostgreSQL.
3. Add the `backend` directory as a service.
4. Set `DATABASE_URL` to the Railway PostgreSQL URL, changing the prefix to `postgresql+psycopg://` if needed.
5. Set `API_KEY` and `CORS_ORIGINS`.
6. Railway runs the seed and starts Uvicorn using `railway.json`.

## Web client

Serve `web/` through Live Server or another static server. Change `web/config.js` to the Railway API URL. The client switches to demonstration telemetry when the API is unavailable.

## MATLAB

```matlab
app = PowerGridSunApp;
buildPowerGridSunModel;
```

Use `configurePython` with the Python executable from the backend virtual environment when calling pandas or scikit-learn directly from MATLAB.

## Database policy

All persistent SQL data uses PostgreSQL. Browser storage is not an operational system of record. MATLAB and web clients communicate with PostgreSQL only through FastAPI.

## Version

`v4.0.0 — Power Grid Sun Foundation`
