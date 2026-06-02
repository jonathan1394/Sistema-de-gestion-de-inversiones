# Correcciones v1 - CriptoLab

Este documento consolida las correcciones detectadas durante el analisis de integraciones del proyecto. El foco principal es eliminar errores que pueden provocar fallos en runtime y ordenar la deuda tecnica que afecta integraciones entre API, core Python, dashboard, frontend, configuracion y base de datos.

## Resumen Ejecutivo

| Prioridad | Items | Impacto |
|-----------|-------|---------|
| Alta | C1, C2, C3, C4 | Errores de runtime en decision engine y API de riesgo |
| Media | W1, W2, W3, W6, W7, W8, W10 | Deuda tecnica, duplicacion, configuracion y estado incompleto |
| Baja | W4, W5 | Lecturas directas de YAML que saltan el sistema de configuracion |

## Estado Detectado

- Los cambios recientes fueron principalmente de frontend.
- El tipado de `frontend/src/app/overview/page.tsx` fue corregido (`apiGet<any>` -> `apiGet<Config>`).
- Se agrego la pagina `frontend/src/app/ranking/page.tsx`.
- C1, C2, C3, C4, W1, W3, W4, W5, W6, W7 y W8 fueron corregidos.
- `pytest` pasa completo: 119 tests.
- Se agrego prueba de contrato para `POST /api/v1/risk/evaluate`.
- Se corrigio el `PytestCollectionWarning` de `quality/validators/test_validator.py` marcando `TestValidator.__test__ = False`.
- `TestValidator` ahora registra como error la falta de tests requeridos en `must_have_tests_for`.
- `QualityAgent` ahora ejecuta `ruff` y `mypy` si estan instalados; si faltan, lo reporta como warning sin romper el flujo local.
- Se eliminaron 8 stubs `tests/test_app_*.py`; el total bajo porque se removieron tests artificiales de `assert True`.
- `TestValidator` ahora reconoce tests reales sin requerir el prefijo `test_app_`.
- La convención de nombres de tests quedo estabilizada sin prefijo `test_app_`.
- Las credenciales Binance ahora viven en `AppConfig` desde variables de entorno y no desde YAML.
- `load_settings()` emite warning si detecta credenciales Binance o Telegram en `settings.yaml`.
- Se agregaron tests para `backtesting.metrics`, `data.binance_client` y `database.migrations`.
- `ruff` y `mypy` no pudieron ejecutarse en el entorno actual porque los comandos no estan instalados.

---

## Correcciones de Alta Prioridad

### C1 - `PortfolioState` mal construido en decision engine

**Estado:** Corregido.

**Archivo:** `app/governance/decision_engine.py`  
**Lineas:** 177-183  
**Severidad:** Critica

### Problema

Se construye `PortfolioState` con campos que no existen:

```python
portfolio_state = PortfolioState(
    total_value=settings.capital.initial_usdt,
    cash=settings.capital.initial_usdt,
    positions={},
    exposure_pct=0.0,
    altcoin_exposure_pct=0.0,
)
```

El dataclass real espera:

```python
PortfolioState(
    total_capital: float,
    cash: float,
    positions: dict[str, float],
    asset_classes: dict[str, str],
)
```

### Correccion propuesta

```python
portfolio_state = PortfolioState(
    total_capital=settings.capital.initial_usdt,
    cash=settings.capital.initial_usdt,
    positions={},
    asset_classes={},
)
```

### Validacion

- Ejecutar una evaluacion de decision desde API o script.
- Verificar que no aparece `TypeError: unexpected keyword argument`.

---

### C2 - Acceso incorrecto a `settings.prospecting`

**Estado:** Corregido.

**Archivo:** `app/governance/decision_engine.py`  
**Lineas:** 130-137  
**Severidad:** Critica

### Problema

`settings.prospecting` es un `dict`, pero se accede como objeto:

```python
settings.prospecting.recommendation.invertir_threshold
```

Esto provoca:

```text
AttributeError: 'dict' object has no attribute 'recommendation'
```

### Correccion propuesta

Usar acceso por diccionario con defaults:

```python
recommendation_cfg = settings.prospecting.get("recommendation", {})

invertir_threshold = recommendation_cfg.get("invertir_threshold", 0.75)
vigilar_threshold = recommendation_cfg.get("vigilar_threshold", 0.60)
neutral_threshold = recommendation_cfg.get("neutral_threshold", 0.40)
evitar_threshold = recommendation_cfg.get("evitar_threshold", 0.0)
```

### Validacion

- Ejecutar `evaluate_investment_decision()` para un prospecto con score alto.
- Verificar que no hay `AttributeError`.

---

### C3 - Campos incorrectos de `ExposureCheckResult` en API de riesgo

**Estado:** Corregido.

**Archivo:** `app/api/routes/risk.py`  
**Lineas:** 126-131  
**Severidad:** Critica

### Problema

Se accede a campos que no existen en `ExposureCheckResult`:

```python
decision.exposure.asset_exposure_pct
decision.exposure.total_exposure_pct
decision.exposure.altcoin_exposure_pct
```

Campos reales:

```python
current_asset_exposure_pct
current_total_exposure_pct
proposed_additional_pct
asset_exposure_after_pct
total_exposure_after_pct
max_asset_pct
max_total_pct
max_altcoin_pct
```

### Correccion propuesta

```python
data["exposure"] = {
    "approved": decision.exposure.approved,
    "rejection_reason": decision.exposure.rejection_reason,
    "current_asset_exposure_pct": decision.exposure.current_asset_exposure_pct,
    "current_total_exposure_pct": decision.exposure.current_total_exposure_pct,
    "proposed_additional_pct": decision.exposure.proposed_additional_pct,
    "asset_exposure_after_pct": decision.exposure.asset_exposure_after_pct,
    "total_exposure_after_pct": decision.exposure.total_exposure_after_pct,
    "max_asset_pct": decision.exposure.max_asset_pct,
    "max_total_pct": decision.exposure.max_total_pct,
    "max_altcoin_pct": decision.exposure.max_altcoin_pct,
}
```

### Validacion

- Llamar `POST /api/v1/risk/evaluate` con una propuesta valida.
- Confirmar que la respuesta incluye `exposure` sin `AttributeError`.

---

### C4 - `PortfolioState` mal construido en API de riesgo

**Estado:** Corregido.

**Archivo:** `app/api/routes/risk.py`  
**Lineas:** 76-82  
**Severidad:** Critica

### Problema

Mismo patron que C1:

```python
portfolio = PortfolioState(
    total_value=float(portfolio_in.get("total_value", proposal.capital)),
    cash=float(portfolio_in.get("cash", proposal.capital)),
    positions=dict(portfolio_in.get("positions", {}) or {}),
    exposure_pct=float(portfolio_in.get("exposure_pct", 0.0)),
    altcoin_exposure_pct=float(portfolio_in.get("altcoin_exposure_pct", 0.0)),
)
```

### Correccion propuesta

```python
portfolio = PortfolioState(
    total_capital=float(portfolio_in.get("total_capital", proposal.capital)),
    cash=float(portfolio_in.get("cash", proposal.capital)),
    positions=dict(portfolio_in.get("positions", {}) or {}),
    asset_classes=dict(portfolio_in.get("asset_classes", {}) or {}),
)
```

### Consideracion de compatibilidad

Si el frontend o clientes externos ya envian `total_value`, se puede aceptar como alias temporal:

```python
total_capital=float(portfolio_in.get("total_capital", portfolio_in.get("total_value", proposal.capital)))
```

Como el proyecto aun esta en migracion y no hay consumidores externos estables, la opcion minima recomendada es usar `total_capital`.

### Validacion

- Llamar `POST /api/v1/risk/evaluate`.
- Confirmar que el endpoint no falla antes de llegar a `RiskManager.evaluate()`.

---

## Correcciones de Prioridad Media

### W1 - `max_total_pct=1.0` hardcodeado

**Estado:** Corregido.

**Archivo:** `app/governance/decision_engine.py`  
**Linea:** 201

### Problema

El limite total de exposicion se pasa como `1.0`, ignorando la configuracion real:

```python
max_total_pct=1.0
```

### Correccion propuesta

Usar el valor de configuracion:

```python
max_total_pct=settings.risk.max_total_exposure_pct
```

### Validacion

- Confirmar que `RiskManager` recibe el limite de `settings.yaml`.
- Agregar o ajustar test si existe cobertura para `evaluate_investment_decision()`.

---

### W2 - `settings.policy.version` inexistente

**Archivo:** `app/governance/decision_engine.py`  
**Linea:** 232

### Problema

`AppConfig` no tiene campo `policy`. El codigo esta protegido con `hasattr`, por lo que no rompe runtime, pero siempre registra `None`.

### Opciones

**Opcion minima:** Mantener `None` y documentar que no existe versionado de politica aun.

**Opcion completa:** Agregar seccion `policy` a `settings.yaml` y representarla en `AppConfig`.

### Recomendacion

Mantener la opcion minima para esta version de correcciones y mover el versionado de politica a una fase posterior.

---

### W3 - `decision_log.py` re-lee settings en cada llamada

**Estado:** Corregido.

**Archivo:** `app/governance/decision_log.py`  
**Lineas:** 57, 111

### Problema

`log_decision()` y `get_recent_decisions()` llaman `load_settings()` internamente cada vez.

### Correccion propuesta

Aceptar `settings` opcional como parametro:

```python
def log_decision(entry: DecisionLogEntry, settings: AppConfig | None = None) -> str:
    settings = settings or load_settings()
    ...
```

```python
def get_recent_decisions(..., settings: AppConfig | None = None) -> list[DecisionLogEntry]:
    settings = settings or load_settings()
    ...
```

### Validacion

- Confirmar que los callers actuales siguen funcionando sin cambios.
- Donde ya exista `settings`, pasarlo para evitar I/O redundante.

---

### W6 - Schema duplicado en `paper_trading/storage.py`

**Estado:** Corregido.

**Archivo:** `app/paper_trading/storage.py`  
**Lineas:** 39-74

### Problema

`init_portfolio_tables()` duplica las tablas que ya define `app/database/migrations.py`.

### Correccion propuesta

Delegar en migraciones:

```python
from app.database.migrations import run_migrations

def init_portfolio_tables(conn: sqlite3.Connection) -> None:
    run_migrations(conn)
```

### Validacion

- Ejecutar tests de storage y portfolio.
- Verificar que no hay divergencia de columnas.

---

### W7 y W8 - Conexiones redundantes en ranking/prospecting

**Estado:** Corregido.

**Archivos:**

- `app/prospecting/ranking.py`
- `app/api/routes/prospecting.py`

### Problema

`generate_ranking()` llama internamente `load_settings()` y `get_connection()`, aunque los endpoints ya tienen ambos recursos.

### Correccion propuesta

Modificar firma:

```python
def generate_ranking(
    prospects: list[Prospect],
    settings: AppConfig | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[AssetRanking]:
    settings = settings or load_settings()
    conn = conn or get_connection(settings.database.path)
    ...
```

Actualizar `app/api/routes/prospecting.py` para pasar `settings` y `conn`.

### Validacion

- `GET /api/v1/prospecting/ranking`
- `GET /api/v1/prospecting/decision/{symbol}`

---

### W10 - Circuit breakers stateless en API

**Archivo:** `app/api/routes/risk.py`  
**Linea:** 54

### Problema

`GET /api/v1/risk/circuit-breakers` devuelve:

```json
{"state": "stateless"}
```

Esto no expone estado real del circuito.

### Correccion propuesta

Para v1, mantener el comportamiento actual pero documentar que es una limitacion del MVP. La exposicion de estado real requiere persistir o compartir instancia de `CircuitBreakers` entre requests.

### Recomendacion

No corregir en el mismo parche que los bugs criticos. Mover a una mejora de arquitectura.

---

## Correcciones de Prioridad Baja

### W4 - Dashboard lee YAML directo

**Estado:** Corregido.

**Archivos:**

- `app/dashboard/pages/overview.py`
- `app/dashboard/pages/risk.py`
- `app/dashboard/pages/market_analysis.py`
- `app/dashboard/pages/prospects.py`
- `app/dashboard/pages/alerts.py`

### Problema

Varios archivos usan `yaml.safe_load(open("settings.yaml"))`, saltandose `load_settings()` y las variables de entorno.

### Correccion propuesta

Usar `load_settings()` o recibir `config` desde `app/dashboard/main.py`.

### Validacion

- Ejecutar dashboard.
- Verificar que `KILL_SWITCH`, `APP_MODE` y `DATABASE_PATH` desde env se reflejan correctamente.

---

### W5 - `alert_monitor.py` lee YAML directo

**Estado:** Corregido.

**Archivo:** `scripts/alert_monitor.py`  
**Lineas:** 30-36

### Problema

`_load_alerts_config()` lee `settings.yaml` directamente.

### Correccion propuesta

Usar `load_settings()`:

```python
def _load_alerts_config() -> dict:
    settings = load_settings()
    return settings.alerts
```

### Validacion

- Ejecutar `python -m scripts.alert_monitor history`.
- Ejecutar `python -m scripts.alert_monitor monitor --once` si existe modo compatible o probar con timeout corto.

---

## Orden de Implementacion Recomendado

### Fase 1 - Correcciones criticas

1. Corregir C1 en `app/governance/decision_engine.py`.
2. Corregir C2 en `app/governance/decision_engine.py`.
3. Corregir C4 en `app/api/routes/risk.py`.
4. Corregir C3 en `app/api/routes/risk.py`.

### Fase 2 - Limpieza media sin cambio funcional amplio

1. Corregir W1 en `app/governance/decision_engine.py`.
2. Ajustar W3 en `app/governance/decision_log.py` con parametro opcional.
3. Ajustar W6 delegando storage init a migrations.
4. Ajustar W7 y W8 para reducir conexiones redundantes.

### Fase 3 - Config y dashboard

1. Corregir W4 en paginas Streamlit.
2. Corregir W5 en `scripts/alert_monitor.py`.
3. Mantener W10 como limitacion documentada hasta definir estado persistente de circuit breakers.

---

## Comandos de Verificacion

Ejecutar desde la raiz del proyecto:

```bash
ruff check app/ tests/
mypy app/
pytest
python -m quality.quality_agent --check-all
```

Para endpoints API:

```bash
python -m scripts.run_api
```

Luego probar manualmente:

```text
GET  /api/v1/risk/limits
GET  /api/v1/risk/status
POST /api/v1/risk/evaluate
GET  /api/v1/prospecting/ranking
GET  /api/v1/prospecting/decision/BTCUSDT
```

---

## Definition of Done

Una correccion de este documento se considera terminada cuando:

1. El bug deja de reproducirse.
2. El endpoint o funcion afectada responde sin excepciones.
3. No se agregan accesos a campos inexistentes.
4. El comportamiento mantiene modo seguro por defecto.
5. Los tests pasan.
6. `python -m quality.quality_agent --check-all` pasa antes de commit.
