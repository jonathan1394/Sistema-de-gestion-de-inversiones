\# Plan de Migracion Web (Opcion B)

Este documento describe el plan para evolucionar CriptoLab a una web mas estable,
manteniendo el core en Python y construyendo un frontend moderno en Node.js.

\## Objetivo

- Mantener intacto el core (datos, backtesting, riesgo, paper trading, prospecting).
- Reemplazar el dashboard Streamlit por una aplicacion web Next.js mas robusta.
- Exponer la logica existente via una API REST (FastAPI).
- Corte: Streamlit se deja de usar cuando la nueva web este lista.

\## Stack

- Backend API: FastAPI + Uvicorn
- Frontend: Next.js (App Router)
- TypeScript: estricto
- UI/Charts: Tremor (recomendado) o Recharts
- Auth: no (sistema interno)

\## Arquitectura

Flujo principal:

1. Next.js consume la API REST.
2. FastAPI envuelve funciones existentes del proyecto (sin reescribir el core).
3. SQLite se mantiene como storage principal.

Diagrama conceptual:

```text
[Next.js UI] <--> [FastAPI /api/v1] <--> [app/* (Python core)] <--> [SQLite]
```

\## Estructura de carpetas propuesta

```text
app/
  api/                       # NUEVO: capa API
    app.py                   # create_app() + lifespan
    schemas.py               # Pydantic models
    middleware.py            # CORS + error handler
    routes/
      market.py
      backtest.py
      portfolio.py
      risk.py
      prospecting.py
      alerts.py
      decisions.py
      system.py

scripts/
  run_api.py                 # NUEVO: entry point para uvicorn

frontend/                    # NUEVO: Next.js
  src/
    app/                     # App Router
    components/
    lib/
    types/
```

\## Contrato de API (principios)

- Versionado: todo bajo `/api/v1`.
- Respuesta consistente:

```json
{
  "status": "ok",
  "data": {},
  "error": null,
  "meta": {}
}
```

- Paginacion estandar donde aplique: `page`, `limit`.
- Fechas/timestamps: UTC milisegundos o ISO-8601 (definir por endpoint y ser consistente).

\## Endpoints (MVP)

\### System

- `GET /api/v1/system/health`
- `GET /api/v1/system/status`

\### Config

- `GET /api/v1/config` (incluye mode, kill_switch, symbols, timeframes, risk, etc.)

\### Market

- `GET /api/v1/market/candles/{symbol}/{interval}?start_ms=&end_ms=&limit=&desc=`
- `GET /api/v1/market/price/{symbol}`
- `GET /api/v1/market/summary` (multi simbolo)

\### Portfolio (paper)

- `GET /api/v1/portfolio/state`
- `GET /api/v1/portfolio/trades?page=&limit=`
- `GET /api/v1/portfolio/snapshots?page=&limit=`

\### Risk

- `GET /api/v1/risk/limits`
- `GET /api/v1/risk/status`
- `GET /api/v1/risk/circuit-breakers`
- `POST /api/v1/risk/evaluate`

\### Backtest

- `POST /api/v1/backtest/run`
- `GET /api/v1/backtest/strategies`

\### Prospecting

- `GET /api/v1/prospecting/prospects?page=&limit=&status=&min_score=`
- `POST /api/v1/prospecting/scan`
- `GET /api/v1/prospecting/ranking`
- `GET /api/v1/prospecting/decision/{symbol}`

\### Decisions / Governance

- `GET /api/v1/decisions?page=&limit=`

\### Alerts

- `GET /api/v1/alerts/rules`
- `POST /api/v1/alerts/rules`
- `GET /api/v1/alerts/history?page=&limit=`

\## Frontend (Next.js App Router)

\### Rutas

- `/` Overview
- `/market`
- `/assets/[symbol]`
- `/prospects`
- `/backtest`
- `/portfolio`
- `/risk`
- `/alerts`
- `/journal`
- `/decisions`
- `/ranking`
- `/logs`

\### Cliente API

- `frontend/src/lib/api.ts`: fetch tipado, manejo de errores, timeouts.
- En desarrollo, proxy via `next.config.ts` rewrites para evitar CORS.

\## Plan de implementacion (sprints)

\### Sprint 1 (API base)

1. Crear `app/api` con `create_app()`.
2. Agregar endpoints: system, config, market, portfolio (state/trades/snapshots).
3. Agregar `scripts/run_api.py`.

Entregable: API usable para construir Overview.

\### Sprint 2 (API completa + frontend bootstrap)

1. Completar endpoints: backtest, risk, prospecting, alerts, decisions.
2. Crear `frontend/` con Next.js App Router + TS estricto.
3. Agregar Tremor + layout + sidebar.

Entregable: frontend levanta y muestra datos reales del Overview.

\### Sprint 3 (frontend core)

1. Implementar Overview, Market, Asset Detail, Prospects.
2. Ajustar contrato de API segun feedback real.

\### Sprint 4 (frontend restante)

1. Backtest, Portfolio, Risk, Alerts, Decisions, Ranking, Logs, Journal.

\### Sprint 5 (polish + cutover)

1. Responsive.
2. Performance (cache y paginacion).
3. Documentacion actualizada.
4. Dejar Streamlit como legacy opcional, no default.

\## Criterios de corte (para dejar Streamlit)

- Todas las paginas clave existen en Next.js y consumen API.
- Operaciones principales: ver mercado, ver cartera paper, prospecting, backtest, decision log.
- Errores manejados de forma consistente (UI + logs).
- Deploy ejecutable en local con un solo comando (idealmente docker-compose o scripts).
