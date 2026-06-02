# Plan de Migracion Web (Opcion B)

Este documento describe el plan para evolucionar CriptoLab a una web mas estable,
manteniendo el core en Python y construyendo un frontend moderno en Node.js.

---

## Estado Actual (Junio 2026)

### API REST (FastAPI) — COMPLETO

La capa API ya esta implementada y funcional en `app/api/`:

| Ruta | Estado | Notas |
|------|--------|-------|
| `GET /api/v1/system/health` | ✅ | |
| `GET /api/v1/system/status` | ✅ | |
| `GET /api/v1/config` | ✅ | |
| `GET /api/v1/market/candles` | ✅ | |
| `GET /api/v1/market/price` | ✅ | |
| `GET /api/v1/market/summary` | ✅ | |
| `GET /api/v1/portfolio/state` | ✅ | |
| `GET /api/v1/portfolio/trades` | ✅ | |
| `GET /api/v1/portfolio/snapshots` | ✅ | |
| `GET /api/v1/risk/limits` | ✅ | |
| `GET /api/v1/risk/status` | ✅ | |
| `GET /api/v1/risk/circuit-breakers` | ⚠️ | Devuelve `"stateless"` — no persiste estado entre requests |
| `POST /api/v1/risk/evaluate` | ✅ | |
| `POST /api/v1/backtest/run` | ✅ | |
| `GET /api/v1/backtest/strategies` | ✅ | |
| `GET /api/v1/prospecting/prospects` | ✅ | |
| `POST /api/v1/prospecting/scan` | ✅ | |
| `GET /api/v1/prospecting/ranking` | ✅ | |
| `GET /api/v1/prospecting/decision` | ✅ | |
| `GET /api/v1/decisions` | ✅ | |
| `GET /api/v1/alerts/rules` | ✅ | |
| `POST /api/v1/alerts/rules` | ⚠️ | Acepta payload pero NO persiste (devuelve `accepted: true` sin guardar) |
| `GET /api/v1/alerts/history` | ✅ | |

Entry point: `scripts/run_api.py` — funciona con `python -m scripts.run_api`.

### Frontend (Next.js) — EN PROGRESO

Estructura actual en `frontend/`:

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx            # Layout principal + sidebar
│   │   ├── page.tsx              # Landing / home
│   │   ├── globals.css           # Estilos globales
│   │   ├── page.module.css
│   │   ├── components/
│   │   │   ├── Nav.tsx           # Navegacion lateral
│   │   │   └── ui.tsx            # Componentes UI base
│   │   ├── overview/page.tsx
│   │   ├── market/
│   │   │   ├── page.tsx
│   │   │   └── market-controls.tsx
│   │   ├── prospects/
│   │   │   ├── page.tsx
│   │   │   └── prospecting-actions.tsx
│   │   ├── backtest/
│   │   │   ├── page.tsx
│   │   │   └── runner.tsx
│   │   ├── portfolio/
│   │   │   ├── page.tsx
│   │   │   └── portfolio-actions.tsx
│   │   ├── risk/
│   │   │   ├── page.tsx
│   │   │   └── risk-evaluator.tsx
│   │   ├── alerts/
│   │   │   ├── page.tsx
│   │   │   └── alerts-actions.tsx
│   │   └── decisions/
│   │       ├── page.tsx
│   │       └── decisions-actions.tsx
│   └── lib/
│       └── api.ts                # Cliente API tipado
├── package.json                  # Next 16, React 19, TypeScript 5
├── tsconfig.json
├── next.config.ts
└── Dockerfile
```

**Paginas implementadas:** overview, market, prospects, ranking, backtest, portfolio, risk, alerts, decisions.
**Paginas faltantes:** asset detail (`/assets/[symbol]`), journal, logs.

### Bugs y Deuda Tecnica Identificados

| Severidad | Archivo | Linea | Descripcion |
|-----------|---------|-------|-------------|
| **BUG** | `app/governance/decision_engine.py` | 177-183 | `PortfolioState()` construido con kwargs incorrectos (`total_value`/`cash`/`exposure_pct`/`altcoin_exposure_pct` vs `total_capital`/`cash`/`positions`/`asset_classes`) |
| **BUG** | `app/governance/decision_engine.py` | 232 | `settings.policy.version` — `AppConfig` no tiene atributo `policy` |
| **BUG** | `scripts/daily_report.py` | 268 | `settings.app.kill_switch` — `AppConfig.kill_switch` es directo, no anidado |
| **BUG** | `scripts/daily_report.py` | 449 | `settings.get("alerts", {})` — `settings` es dataclass, no dict |
| **BUG** | `scripts/admin_console.py` | 130-131 | Argumentos `--fast`/`--slow` pasados a `run_paper_trading` que no los acepta |
| **BUG** | `scripts/admin_console.py` | 149-151 | Falta subcomando `scan` al llamar `run_prospecting` |
| **BUG** | `scripts/admin_console.py` | 173 | `--strategies` pasado a `compare_strategies` que no lo acepta |
| Deuda tecnica | `app/api/routes/alerts.py` | 32 | `POST /rules` no persiste reglas |
| Deuda tecnica | `app/api/routes/risk.py` | 55 | Circuit breaker stateless |
| Deuda tecnica | 3 archivos | — | `analyze_timeframe()` / `compute_confluence()` triplicadas en `market_decision.py`, `market_analysis.py` y `asset_detail.py` |
| Deuda tecnica | `asset_detail.py`, `prospects.py` | — | `commission=0.0` hardcodeado en vez de usar `settings.fees.trading_fee_pct` |
| Deuda tecnica | `overview.py`, `risk.py` | — | Lectura directa de `settings.yaml` desde disco en vez de config ya cargada |

---

## Objetivo

- Mantener intacto el core (datos, backtesting, riesgo, paper trading, prospecting).
- Reemplazar el dashboard Streamlit por una aplicacion web Next.js mas robusta.
- Exponer la logica existente via una API REST (FastAPI). **YA IMPLEMENTADO.**
- Corte: Streamlit se deja de usar cuando la nueva web este lista.

---

## Stack

- Backend API: FastAPI + Uvicorn — **YA IMPLEMENTADO**
- Frontend: Next.js (App Router) — **YA INICIADO**
- TypeScript: estricto
- UI: Tremor (recomendado) o componentes propios — **Actualmente usa CSS modules + componentes propios**
- Auth: no (sistema interno)

---

## Arquitectura

Flujo principal:

1. Next.js consume la API REST. — **EN PROGRESO**
2. FastAPI envuelve funciones existentes del proyecto (sin reescribir el core). — **COMPLETO**
3. SQLite se mantiene como storage principal.

Diagrama conceptual:

```text
[Next.js UI] <--> [FastAPI /api/v1] <--> [app/* (Python core)] <--> [SQLite]
```

---

## Estructura de carpetas (estado actual)

```text
app/
  api/                       # COMPLETO: capa API funcional
    app.py                   # create_app() + lifespan
    schemas.py               # Pydantic models
    middleware.py            # CORS + error handler
    routes/
      system.py
      config.py
      market.py
      backtest.py
      portfolio.py
      risk.py
      prospecting.py
      alerts.py
      decisions.py

scripts/
  run_api.py                 # COMPLETO: entry point para uvicorn

frontend/                    # EN PROGRESO: Next.js
  src/
    app/                     # App Router
      overview/              # ✅ Implementado
      market/                # ✅ Implementado
      prospects/             # ✅ Implementado
      backtest/              # ✅ Implementado
      portfolio/             # ✅ Implementado
      risk/                  # ✅ Implementado
      alerts/                # ✅ Implementado
      decisions/             # ✅ Implementado
      assets/[symbol]/       # ❌ Pendiente
      journal/               # ❌ Pendiente
      ranking/               # ✅ Implementado
      logs/                  # ❌ Pendiente
    components/
      Nav.tsx                # ✅ Implementado
      ui.tsx                 # ✅ Base UI components
    lib/
      api.ts                 # ✅ Cliente API tipado
    types/                   # ❌ Pendiente
```

---

## Contrato de API (principios)

- Versionado: todo bajo `/api/v1`. — **CUMPLIDO**
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

---

## Plan de implementacion actualizado (sprints)

### Sprint 1 (API base) — COMPLETO

1. ✅ Crear `app/api` con `create_app()`.
2. ✅ Agregar endpoints: system, config, market, portfolio (state/trades/snapshots).
3. ✅ Agregar `scripts/run_api.py`.

### Sprint 2 (API completa + frontend bootstrap) — COMPLETO

1. ✅ Completar endpoints: backtest, risk, prospecting, alerts, decisions.
2. ✅ Crear `frontend/` con Next.js App Router + TS estricto.
3. ✅ Layout + sidebar navegacion + cliente API.

### Sprint 3 (frontend core) — EN PROGRESO

1. ✅ Overview, Market, Prospects, Backtest, Portfolio, Risk, Alerts, Decisions.
2. ❌ Asset Detail (`/assets/[symbol]`) — consumir `GET /market/candles`, `GET /market/price`, `GET /prospecting/decision`.
3. ❌ Journal (`/journal`) — formulario de carga + analisis via AI.
4. ✅ Ranking (`/ranking`) — mostrar `GET /prospecting/ranking`.
5. ❌ Logs (`/logs`) — visor de logs del sistema.

### Sprint 4 (bugs + refactor + deuda tecnica)

1. ❌ Corregir `POST /api/v1/alerts/rules` para persistencia real.
2. ❌ Corregir `GET /api/v1/risk/circuit-breakers` para devolver estado real.
3. ❌ Eliminar codigo duplicado de `analyze_timeframe()` / `compute_confluence()` — refactorizar a `app/prospecting/market_decision.py` y reusar desde dashboard y API.
4. ❌ Corregir `commission=0.0` hardcodeado en dashboard pages.
5. ❌ Reemplazar lectura directa de `settings.yaml` en dashboard por config ya cargada.
6. ❌ Agregar tipos TypeScript compartidos en `frontend/src/types/`.
7. ❌ Agregar Tremor o Recharts para graficos.

### Sprint 5 (polish + cutover)

1. ❌ Responsive.
2. ❌ Performance (cache y paginacion).
3. ❌ Documentacion actualizada (README, setup frontend).
4. ❌ Dejar Streamlit como legacy opcional, no default.

---

## Criterios de corte (para dejar Streamlit)

- [ ] API corrige bugs de persistencia (alerts rules, circuit breakers).
- [ ] Todas las paginas clave existen en Next.js y consumen API.
- [ ] Pagina Asset Detail funcional con datos reales.
- [ ] Operaciones principales: ver mercado, ver cartera paper, prospecting, backtest, decision log.
- [ ] Errores manejados de forma consistente (UI + logs).
- [ ] Deploy ejecutable en local con un solo comando (docker-compose o scripts).
- [ ] Types compartidos definidos.
