# Plan de Mejoras — CriptoLab v2

## Estructura del Documento

Dos fases secuenciales, cada una con tareas priorizadas. Cada tarea incluye:
- **Archivos involucrados** (ruta exacta)
- **Qué hacer** (descripción concreta)
- **Por qué** (justificación)
- **Cómo** (orientación técnica)
- **Esfuerzo estimado**

---

# Fase 1: Cimientos — Estabilidad, Calidad y Deuda Técnica Crítica

**Objetivo**: Que el sistema sea correcto, testeable y mantenible antes de agregar nueva funcionalidad.
**Duración estimada**: 2-3 semanas
**Dependencia**: Ninguna externa. Se trabaja directamente sobre `main`.

---

## 1.1 Bugs Críticos y Altos

### Estado de validacion tecnica

Validado contra el codigo actual el 2026-06-02. Esta matriz debe usarse antes de ejecutar la Fase 1 para evitar atacar tareas ya resueltas o con referencias desactualizadas.

| Item | Estado | Nota |
|------|--------|------|
| 1.1.1 Safety checks attribute name | Corregido | `safety_checks.py` usa `perms.can_withdraw_assets`. Validado con tests enfocados. |
| 1.1.2 Circuit breakers loss limits | Corregido | `daily_loss_pct` y `weekly_loss_pct` se comparan en `check_trading_allowed()`. Validado con tests nuevos. |
| 1.1.3 Missing return en simulator | Ya corregido | `_process_buy_signal()` ya retorna tras `decision.approved == False` y tras `position_size is None`. No ejecutar salvo que se reabra el bug. |
| 1.1.4 DCA double adjustment | Corregido | `below_ema` solo reduce mediante `reduce_multiplier`; se elimino la segunda reduccion. |
| 1.1.5 Dashboard prices BTC bug | Corregido | `main.py` consulta precio por simbolo antes de actualizar portfolio. |
| 1.1.6 Timestamp extraction | Corregido | Las estrategias usan `pd.Timestamp(idx)` de forma consistente. |
| 1.1.7 Ranking missing import | Corregido | Se reemplazo `List[AssetRanking]` por `list[AssetRanking]`. |

Referencia adicional: `docs/correcciones_v1.md` contiene otros bugs criticos de integracion que deben resolverse antes o junto con esta Fase 1: `PortfolioState` mal construido y campos incorrectos de `ExposureCheckResult`.

### 1.1.1 Safety checks — AttributeError por nombre de atributo incorrecto

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/execution/safety_checks.py:59`, `app/execution/binance_executor.py:40` |
| **Qué** | Corregir `perms.can_withdraw` → `perms.can_withdraw_assets` |
| **Por qué** | `PermissionCheck` define `can_withdraw_assets` (línea 40), pero `safety_checks.py` accede `can_withdraw`. Causa `AttributeError` en ejecución. |
| **Cómo** | Cambiar `perms.can_withdraw` por `perms.can_withdraw_assets` en `safety_checks.py` línea 59. |
| **Test** | Verificar que `check_binance_permissions()` no lance `AttributeError`. |
| **Esfuerzo** | 15 minutos |

### 1.1.2 Circuit breakers — Loss limits no verificados

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/risk/circuit_breakers.py` |
| **Qué** | Implementar la verificación de `max_daily_loss_pct` y `max_weekly_loss_pct` dentro de `check_trading_allowed()` |
| **Por qué** | Los límites de pérdida diaria/semanal se almacenan en el estado pero nunca se verifican. Es un agujero de seguridad en el risk management. |
| **Cómo** | En `check_trading_allowed()`, antes de retornar, comparar `self._state.daily_loss_pct` contra `self._max_daily_loss` y `self._state.weekly_loss_pct` contra `self._max_weekly_loss`. Si exceden, retornar `CircuitBreakerResult(trading_allowed=False, reason="...")` |
| **Test** | Test que verifica: 1) pérdida diaria dentro del límite → permitido, 2) pérdida diaria excede → bloqueado, 3) reseteo diario restablece el contador |
| **Esfuerzo** | 2-4 horas |

### 1.1.3 Paper trading simulator — Missing return tras reject

| Campo | Valor |
|-------|-------|
| **Estado validado** | Ya corregido en el codigo actual. Mantener como item historico/documental. |
| **Archivo** | `app/paper_trading/simulator.py:115-117` |
| **Qué** | Agregar `return` después de `self._trades_rejected += 1` en `_process_buy_signal` |
| **Por qué** | El código incrementa el contador de rechazos pero continúa ejecutando, creando una orden con `quantity=None` que causa error downstream. |
| **Cómo** | Insertar `return signal` (o `return None`) después de la línea 117. |
| **Test** | Simular una señal de compra que falla en position sizing → verificar que no se crea ninguna orden. |
| **Esfuerzo** | 15 minutos |

### 1.1.4 DCA dinámico — Ajuste duplicado de position_size_pct

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/strategies/dca_dynamic.py:56-61` |
| **Qué** | Eliminar la doble reducción de `position_size_pct` cuando `below_ema` es True |
| **Por qué** | Cuando `below_ema` es True, el multiplier se reduce (línea 57: `multiplier *= reduce_multiplier`) y luego `position_size_pct` se multiplica por 0.5 otra vez (línea 60). Esto aplica el ajuste dos veces. |
| **Cómo** | Decidir una estrategia: o se aplica el `reduce_multiplier` al multiplier (correcto) O se aplica el 0.5 directo a `position_size_pct`, pero no ambos. Sugerencia: mantener solo la lógica del multiplier y eliminar el `*= 0.5` extra. |
| **Test** | Generar señal con `below_ema=True` y verificar que `position_size_pct` sea exactamente `0.1 * multiplier * reduce_multiplier` (una sola reducción). |
| **Esfuerzo** | 1-2 horas |

### 1.1.5 Dashboard — ETHUSDT y SOLUSDT toman precio de BTC

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/dashboard/main.py:232` |
| **Qué** | Asignar el precio correcto a cada símbolo en el diccionario de precios |
| **Por qué** | Línea 232 crea `{"BTCUSDT": latest_price, "ETHUSDT": latest_price, "SOLUSDT": latest_price}` — todas las monedas toman el precio de BTC, causando valuación incorrecta del portafolio. |
| **Cómo** | Consultar el precio actual de cada símbolo individualmente desde `market_data.get_candles()` o desde `BinanceClient`. Ejemplo: `prices = {sym: get_latest_price(sym) for sym in symbols}` |
| **Test** | Verificar visualmente en dashboard que ETHUSDT y SOLUSDT muestren precios diferentes a BTC. |
| **Esfuerzo** | 2-3 horas |

### 1.1.6 Estrategias — Timestamp extraction bug en iterrows

**Aplica a**: `app/strategies/moving_average.py:29`, `rsi_strategy.py:43`, `trend_following.py:58`, `dca_dynamic.py` (línea similar)

| Campo | Valor |
|-------|-------|
| **Qué** | Reemplazar `pd.Timestamp(row.get("timestamp", idx))` por `data.index[idx]` |
| **Por qué** | `iterrows()` devuelve `(index, Series)`. La `Series` no tiene atributo `"timestamp"` a menos que el DataFrame lo tenga como columna. Si el índice es `DatetimeIndex`, `data.index[idx]` funciona correctamente. |
| **Cómo** | En cada estrategia, cambiar: `timestamp = pd.Timestamp(row.get("timestamp", idx))` → `timestamp = data.index[idx]`. Asumiendo que `idx` es el índice de iteración. |
| **Esfuerzo** | 30 minutos (4 archivos) |

### 1.1.7 Ranking page — Missing import de List

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/dashboard/pages/ranking.py:36` |
| **Qué** | Agregar `from typing import List` |
| **Por qué** | Se usa `rankings: List[AssetRanking]` pero `List` no está importado → `NameError` al cargar la página. |
| **Cómo** | Agregar import en la cabecera del archivo. |
| **Esfuerzo** | 5 minutos |

---

## 1.2 Seguridad Inmediata

### 1.2.1 Centralizar credenciales Binance en config.py

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/config.py`, todos los scripts/lugares que cargan credenciales |
| **Qué** | Agregar `binance_api_key: str = ""` y `binance_api_secret: str = ""` a `AppConfig`, cargados exclusivamente de `os.getenv()` (nunca de YAML). |
| **Por qué** | Hoy cada llamador carga las credenciales manualmente con `os.getenv()`. Si alguien las pone en `settings.yaml` y lo commitea, quedan expuestas. |
| **Cómo** | 1) Agregar campos a `AppConfig` como `field(repr=False)` para que no se logeen. 2) En `load_settings()`, leer de `os.getenv("BINANCE_API_KEY")` y `os.getenv("BINANCE_API_SECRET")`. 3) Agregar warning si detecta valores en YAML. 4) Actualizar todos los callers para recibir credenciales desde config. |
| **Esfuerzo** | 3-4 horas |

### 1.2.2 Validar que Telegram token no esté en settings.yaml

| Campo | Valor |
|-------|-------|
| **Archivos** | `settings.yaml`, `app/alerts/channels.py`, `app/config.py` |
| **Qué** | En `load_settings()`, verificar que `bot_token` y `chat_id` en settings.yaml estén vacíos. Si no, emitir warning de seguridad. |
| **Por qué** | settings.yaml se commitea. Si alguien pone el token real ahí, queda en el historial de git para siempre. |
| **Cómo** | En `load_settings()`, tras cargar YAML, verificar `alerts.telegram.bot_token` no sea `None`/no vacío. Si tiene valor que no sea placeholder, loggear `logging.warning("TELEGRAM BOT TOKEN DETECTED IN settings.yaml! Move to env var TELEGRAM_BOT_TOKEN")` |
| **Esfuerzo** | 1 hora |

---

## 1.3 Tests para Módulos Críticos

**Nota general**: Usar `conftest.py` existente que agrega project root al `sys.path`. Usar `pytest` con fixtures en memoria. Seguir el patrón de los tests existentes (ej: `test_risk_position_sizing.py`).

### 1.3.1 Tests para circuit_breakers.py

| Campo | Valor |
|-------|-------|
| **Archivo test** | `tests/test_risk_circuit_breakers.py` |
| **Casos**: | |
| | Crear `CircuitBreakers` con defaults → kill switch activo por defecto → trading bloqueado |
| | `record_trade` con pérdida → consecutivas se incrementan |
| | `record_trade` con ganancia → consecutivas se resetean a 0 |
| | Límite de trades diarios → abrir N trades, cerrar 1, abrir otro → límite se alcanza |
| | Límite de pérdida diaria → acumular pérdidas hasta exceder `max_daily_loss_pct` → `check_trading_allowed` retorna bloqueado (este test falla hoy, pasa tras fix 1.1.2) |
| | Límite de pérdida semanal → mismo patrón |
| | `_reset_if_new_period` → simular cambio de día y verificar reseteo |
| | `kill_switch` se puede activar/desactivar via property |
| **Esfuerzo** | 4-6 horas |

### 1.3.2 Tests para risk_manager.py

| Campo | Valor |
|-------|-------|
| **Archivo test** | `tests/test_risk_risk_manager.py` |
| **Casos**: | |
| | `evaluate()` con todo aprobado → `approved=True` |
| | `evaluate()` con circuit breaker bloqueando → `approved=False` con razón |
| | `evaluate()` con stop-loss inválido → rechazado |
| | `evaluate()` con position sizing → tamaño calculado correctamente |
| | `evaluate()` con exposure limits excedidos → rechazado |
| | Probar cada paso fallando individualmente |
| | Verificar que el orden de evaluación es: CB → SL → PS → EL |
| **Esfuerzo** | 4-6 horas |

### 1.3.3 Tests para config.py

| Campo | Valor |
|-------|-------|
| **Archivo test** | `tests/test_config.py` |
| **Casos**: | |
| | `load_settings()` con settings.yaml existente → carga correcta |
| | `load_settings()` con archivo inexistente → `FileNotFoundError` |
| | Env var `APP_MODE` sobreescribe `app.mode` en YAML |
| | Env var `KILL_SWITCH` sobreescribe `app.kill_switch` |
| | Env var `DATABASE_PATH` sobreescribe `database.path` |
| | `_to_bool()` con "true"/"True"/"1"/"yes" → `True` |
| | `_to_bool()` con "false"/"False"/"0"/"no" → `False` |
| | `_to_bool()` con valor inválido → default |
| | Valores por defecto cuando YAML no tiene ciertas secciones |
| **Esfuerzo** | 3-4 horas |

### 1.3.4 Tests para backtesting/metrics.py

| Campo | Valor |
|-------|-------|
| **Archivo test** | `tests/test_backtesting_metrics.py` |
| **Casos**: | |
| | Datos con ganancias → Sharpe > 0, profit factor > 1, win rate > 50% |
| | Datos con pérdidas → Sharpe < 0, profit factor < 1, win rate < 50% |
| | Drawdown → precio cae 50% → max_drawdown ≈ 50% |
| | Drawdown → precio sube continuamente → max_drawdown ≈ 0% |
| | CAGR con datos de 1 año → valor razonable |
| | Trades vacíos → manejo de edge case |
| | Trade con PnL exactamente 0 → streak counting no se rompe (ver bug conocido) |
| | Payoff ratio con 100% win rate → no división por cero |
| **Esfuerzo** | 4-6 horas |

### 1.3.5 Tests para binance_client.py

| Campo | Valor |
|-------|-------|
| **Archivo test** | `tests/test_binance_client.py` |
| **Casos**: | |
| | `get_klines()` con símbolo e intervalo válido → dataframe con columnas esperadas |
| | `get_klines()` con error de red → retry y `RuntimeError` |
| | `get_klines()` con límite personalizado → número de filas correcto |
| | `get_klines()` con start/end time → rango filtrado |
| | Mockear `requests.get` para evitar llamadas reales a Binance |
| **Esfuerzo** | 3-4 horas |

### 1.3.6 Tests para migrations.py

| Campo | Valor |
|-------|-------|
| **Archivo test** | `tests/test_database_migrations.py` |
| **Casos**: | |
| | `run_migrations()` crea todas las tablas |
| | `run_migrations()` es idempotente (correr 2 veces no falla) |
| | Cada tabla tiene las columnas esperadas |
| | Índices se crean correctamente |
| **Esfuerzo** | 2-3 horas |

---

## 1.4 Limpieza del Quality System

### 1.4.1 Eliminar stubs test_app_*

| Campo | Valor |
|-------|-------|
| **Archivos** | `tests/test_app_backtesting_engine.py`, `test_app_execution_safety_checks.py`, `test_app_risk_exposure_limits.py`, `test_app_risk_position_sizing.py`, `test_app_risk_stop_loss.py`, `test_app_strategies_base_strategy.py`, `test_app_prospecting_db.py`, `test_app_prospecting_scoring.py` |
| **Qué** | Eliminar estos 8 archivos. **No** eliminar los tests reales (ej: `test_risk_position_sizing.py`). |
| **Por qué** | Solo contienen `assert True` y existen para engañar al `TestValidator`. No aportan cobertura real. |
| **Esfuerzo** | 10 minutos |

### 1.4.2 Renombrar tests con naming consistente

| Campo | Valor |
|-------|-------|
| **Qué** | Unificar los nombres de archivos de test para que sigan una convención única. |
| **Convención propuesta** | `tests/test_<modulo>_<submodulo>.py` — ej: `test_risk_circuit_breakers.py`, `test_backtesting_engine.py`, `test_risk_position_sizing.py` |
| **Por qué** | Hoy hay mezcla de `test_app_*` vs `test_*` que causa confusión y stubs duplicados. |
| **Cómo** | Decidir una convención (sugerencia: sin prefijo `app_` ya que todo está en `app/`) y renombrar consistentemente. Actualizar `rules.yaml` si es necesario. |
| **Esfuerzo** | 1-2 horas |

### 1.4.3 Activar validate_unused_imports()

| Campo | Valor |
|-------|-------|
| **Archivo** | `quality/validators/code_validator.py` |
| **Qué** | Agregar `self.validate_unused_imports()` al método `validate_all()` |
| **Por qué** | El método ya está implementado (parsea AST buscando imports no usados) pero nunca se ejecuta. |
| **Cómo** | Simplemente agregar la llamada en `validate_all()`. Decidir si emite `error` o `warning`. Sugerencia: comenzar como `warning` y subir a `error` en Fase 2. |
| **Esfuerzo** | 15 minutos |

### 1.4.4 Implementar fail_fast en quality agent

| Campo | Valor |
|-------|-------|
| **Archivo** | `quality/quality_agent.py` |
| **Qué** | Leer `rules.yaml → agent → fail_fast` y abortar tras el primer fallo si está activo |
| **Por qué** | El flag está definido en rules.yaml pero `run_all_gates()` ejecuta todos los gates secuencialmente sin importar fallos. |
| **Cómo** | En `run_all_gates()`, si `fail_fast` es `True` y un gate falla, romper el ciclo y no ejecutar los gates restantes. |
| **Esfuerzo** | 1 hora |

### 1.4.5 Hacer que TestValidator falle realmente

| Campo | Valor |
|-------|-------|
| **Archivo** | `quality/validators/test_validator.py` |
| **Qué** | Cambiar `warnings.append()` por `errors.append()` cuando un módulo de `must_have_tests_for` no tenga test correspondiente |
| **Por qué** | Hoy el validador solo emite warnings, nunca causa fallo. El 70% de cobertura objetivo no se enforcea. |
| **Cómo** | Donde se detecta módulo faltante, agregar a `errors` en vez de `warnings`. Opcional: implementar medición real de cobertura con `pytest --cov` y comparar contra `rules.yaml → testing → min_coverage_pct`. |
| **Esfuerzo** | 2-3 horas |

### 1.4.6 Integrar ruff y mypy en quality agent

| Campo | Valor |
|-------|-------|
| **Archivo** | `quality/quality_agent.py` o nuevo `quality/gates/lint_gate.py` |
| **Qué** | Agregar ejecución de `ruff check app/` y `mypy app/` como parte del quality check |
| **Por qué** | El quality agent reimplementa validaciones simples (AST parsing) que herramientas maduras ya hacen mejor. |
| **Cómo** | Usar `subprocess.run(["ruff", "check", "app/"])` y `subprocess.run(["mypy", "app/"])`. Parsear stdout/stderr para incluir resultados en el reporte. |
| **Esfuerzo** | 3-4 horas |

---

## 1.5 Refactor Estrategias — Vectorización + Stop Loss

### 1.5.1 Migrar estrategias de iterrows a operaciones vectorizadas

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/strategies/moving_average.py`, `rsi_strategy.py`, `trend_following.py`, `dca_dynamic.py`, `rebalance.py` |
| **Qué** | Reemplazar bucles `for idx, row in df.iterrows()` por operaciones vectorizadas con `shift()` |
| **Por qué** | iterrows es ~50x más lento que operaciones vectorizadas en DataFrames grandes. Para backtesting con 10k+ velas, la diferencia es significativa. |
| **Cómo**: | |
| **MA Crossover** | `signal = 0` inicial. `signal[(ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))] = 1` (BUY). `signal[(ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))] = -1` (SELL) |
| **RSI** | `signal[(rsi > oversold_threshold) & (rsi.shift(1) <= oversold_threshold)] = 1` (BUY). Similar para SELL con overbought. |
| **Trend Following** | Mantener `_buy_conditions_met` y `_trend_broken` como checks vectorizados. `entry = buy_conditions & ~buy_conditions.shift(1)` (cruce a True). `exit = trend_broken & ~trend_broken.shift(1)` |
| **DCA** | Calcular drawdown vectorizado: `drawdown = (close - close.rolling(30).max()) / close.rolling(30).max()`. Señal en intervalos con `df.index % interval_days == 0`. |
| **Rebalance** | Similar a DCA, señal en intervalos fijos. |
| **Esfuerzo** | 8-12 horas (los 5 archivos) |

### 1.5.2 Agregar stop_loss y take_profit configurables

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/strategies/base_strategy.py`, todas las estrategias concretas |
| **Qué** | Agregar parámetros `stop_loss_pct` (default 0.02) y `take_profit_pct` (default 0.04) a `BaseStrategy`. Cada estrategia debe poblar `signal.stop_loss` y `signal.take_profit`. |
| **Por qué** | Hoy las señales nunca incluyen stop-loss/take-profit. El backtesting engine los soporta (en `_check_exit`) pero nunca se usan porque están en `None`. |
| **Cómo** | 1) Agregar `stop_loss_pct: float = 0.02` y `take_profit_pct: Optional[float] = 0.04` a `BaseStrategy.__init__`. 2) Al crear cada `Signal`, calcular: `stop_loss = entry_price * (1 - stop_loss_pct)` (long). 3) Para take_profit: `take_profit = entry_price * (1 + take_profit_pct)`. |
| **Esfuerzo** | 4-6 horas |

### 1.5.3 Hacer confidence y risk_score parametrizables

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/strategies/*.py`, `settings.yaml` |
| **Qué** | Reemplazar valores hardcodeados (`confidence=0.6`, `risk_score=0.4`) por parámetros configurables desde settings.yaml |
| **Por qué** | La confianza y riesgo de cada estrategia deben ser ajustables sin modificar código. |
| **Cómo** | Agregar `confidence: float = 0.6` y `risk_score: float = 0.4` a los parámetros de cada estrategia. Leer desde `settings.yaml → strategies → <name> → confidence/risk_score`. |
| **Esfuerzo** | 2-3 horas |

### 1.5.4 Agregar chequeo de minimum_bars

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/strategies/base_strategy.py` o cada estrategia concreta |
| **Qué** | Verificar que `len(data) > slow_period` (o el periodo máximo requerido) antes de generar señales |
| **Por qué** | Si hay menos datos que el periodo del indicador, todos los valores serán NaN y la estrategia genera 0 señales sin advertencia. |
| **Cómo** | En `generate_signals()`, al inicio: `if len(data) < self._min_required_bars: return StrategyResult(signals=[], warning=f"Se requieren al menos {self._min_required_bars} velas")` |
| **Esfuerzo** | 1-2 horas |

### 1.5.5 Unificar representación de porcentajes

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/risk/stop_loss.py:46,83`, `app/risk/position_sizing.py`, `app/risk/circuit_breakers.py`, `app/paper_trading/simulator.py:167-168` |
| **Qué** | Estandarizar todo a formato decimal (`0.03` = 3%). Eliminar multiplicaciones por 100. |
| **Por qué** | Hoy algunos módulos esperan `0.05` (decimal) y otros `5.0` (porcentaje). Esto causa bugs de escala en cálculos de pérdidas/límites. |
| **Cómo**: | |
| | `stop_loss.py:46` `distance_pct=stop_loss_pct * 100` → `distance_pct=stop_loss_pct` |
| | `stop_loss.py:83` mismo cambio |
| | `position_sizing.py:55` `risk_pct = risk_per_trade_pct * 100` → `risk_pct = risk_per_trade_pct` |
| | `simulator.py:167` `realized_pnl / (fill.quantity * fill.price) * 100` → verificar si el resultado se compara con decimal o porcentaje aguas abajo y ajustar |
| | `circuit_breakers.py:90` `daily_loss_pct += abs(pnl_pct)` — verificar que `pnl_pct` que recibe sea decimal |
| **Esfuerzo** | 3-5 horas (requiere rastrear cada sitio que produce o consume porcentajes) |

---

## 1.6 Paper Trading — Fix Simulación

### 1.6.1 VirtualPortfolio.update_prices() con timestamp de simulación

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/paper_trading/virtual_portfolio.py:107` |
| **Qué** | Cambiar `datetime.now(timezone.utc)` para aceptar un parámetro `timestamp: Optional[datetime] = None`. Si no se pasa, usar wall clock. |
| **Por qué** | En backtesting/paper-trading histórico, el timestamp debe ser el de la vela, no el reloj del sistema. |
| **Cómo** | `def update_prices(self, prices: dict, timestamp: Optional[datetime] = None):` y `now = timestamp or datetime.now(timezone.utc)`. Actualizar el callers en `simulator.py` para pasar el timestamp correcto. |
| **Esfuerzo** | 2-3 horas |

### 1.6.2 Registrar trades en circuit breakers desde compras

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/paper_trading/simulator.py` — método `_process_buy_signal` |
| **Qué** | Agregar llamada a `self.circuit_breakers.record_trade()` también cuando se ejecuta una compra |
| **Por qué** | Hoy `_process_sell_signal` registra trades en circuit breakers (para tracking de pérdidas consecutivas), pero `_process_buy_signal` no. Una compra no realizada (por falta de fondos, etc.) debería contar como trade fallido. |
| **Cómo** | Al final de `_process_buy_signal`, después de ejecutar la orden, agregar `self.circuit_breakers.record_trade(...)`. Decidir qué PnL reportar: 0 (la compra en sí no es ganancia/pérdida) o None (evento informativo). |
| **Esfuerzo** | 1-2 horas |

### 1.6.3 Sincronizar VirtualOrderManager con storage.py

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/paper_trading/simulator.py`, `storage.py`, `virtual_orders.py`, `virtual_portfolio.py` |
| **Qué** | Implementar modo write-through: cada operación sobre `VirtualOrderManager` y `VirtualPortfolio` persiste inmediatamente a SQLite |
| **Por qué** | Hoy los objetos en memoria y la base de datos SQLite pueden desincronizarse. Un reinicio del dashboard pierde el estado en memoria. |
| **Cómo** | 1) `PaperTradingSimulator` ya tiene referencia a `db_path` y `storage`. 2) Después de cada `fill` en `VirtualOrderManager`, llamar a `storage.record_trade()`. 3) Después de cada cambio en `VirtualPortfolio`, llamar a `storage.upsert_position()`. 4) Agregar snapshot periódico. Opcional: al iniciar, cargar estado desde DB. |
| **Esfuerzo** | 4-6 horas |

---

## 1.7 Integrar Risk Manager en Backtesting

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/backtesting/engine.py`, `app/risk/risk_manager.py` |
| **Qué** | Hacer que `BacktestEngine.run()` pase cada señal propuesta por `RiskManager.evaluate()` antes de ejecutarla |
| **Por qué** | Hoy el backtesting usa `signal.position_size_pct` directamente, sin pasar por risk checks. Los backtests muestran resultados irreales comparados con paper/real trading, donde el RiskManager puede rechazar trades. |
| **Cómo**: | |
| | 1) En `BacktestEngine.__init__`, aceptar `risk_manager: Optional[RiskManager] = None` |
| | 2) En el loop principal, antes de `_enter_position`, llamar a: `decision = risk_manager.evaluate(TradeProposal(...))` |
| | 3) Si `decision.approved == False`, saltar la señal y registrar rechazo |
| | 4) Si es aprobado, usar `decision.position_size` en lugar de `sig.position_size_pct` |
| | 5) Usar `decision.stop_loss` como `stop_loss` en la posición |
| | 6) Agregar `rejected_signals: List[dict]` al `BacktestResult` para auditoría |
| **Dependencia** | Requiere que 1.3.1 y 1.3.2 estén completos (tests de circuit_breakers y risk_manager) |
| **Esfuerzo** | 6-8 horas |
| **Impacto** | Alto — los backtests reflejarán la realidad del risk management |

---

## 1.8 Dashboard — Quick Fixes

### 1.8.1 Eliminar duplicación de funciones helpers

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/dashboard/pages/overview.py`, `portfolio.py`, `assets_detail.py`, `backtest.py`, `prospects.py`, `portfolio_state.py` |
| **Qué** | Mover `_get_portfolio_value()`, `_candles_to_dataframe()`, `_get_current_price()` a `app/dashboard/helpers.py` e importar desde allí |
| **Por qué** | Estas 3 funciones están definidas en 2+ lugares cada una. Duplicación = mantenimiento difícil + bugs. |
| **Cómo**: | |
| | Crear `app/dashboard/helpers.py` |
| | Mover `_get_portfolio_value()` desde `overview.py:13-27` y `portfolio_state.py:14-25` |
| | Mover `_candles_to_dataframe()` desde `backtest.py` y `asset_detail.py` |
| | Mover `_get_current_price()` desde `prospects.py` y `asset_detail.py` |
| | Actualizar imports en todos los archivos fuente |
| | Eliminar las funciones duplicadas de los archivos originales |
| **Esfuerzo** | 3-4 horas |

### 1.8.2 Unificar capital inicial dinámico

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/dashboard/pages/overview.py:240-241`, `portfolio.py`, `portfolio_state.py` |
| **Qué** | Reemplazar `1000.0` hardcodeado por `st.session_state.portfolio_capital` (que se carga desde `settings.yaml → capital → initial_usdt`) |
| **Por qué** | El capital inicial hardcodeado en 5+ lugares hace que cambiar el capital en settings.yaml no se refleje en el dashboard. |
| **Esfuerzo** | 2-3 horas |

### 1.8.3 Manejo de errores consistente

| Campo | Valor |
|-------|-------|
| **Archivos** | Todos los archivos en `app/dashboard/pages/` |
| **Qué** | Revisar y estandarizar: usar try/except específicos, no `except Exception: continue`. Mostrar errores al usuario via `st.error()` cuando algo falle. |
| **Por qué** | Algunas páginas tragan excepciones silenciosamente, otras crashean el dashboard entero. |
| **Esfuerzo** | 4-6 horas |

---

# Fase 2: Crecimiento — Arquitectura, Features y Producto

**Objetivo**: Escalar la arquitectura, agregar features diferenciadoras, madurar el producto.
**Duración estimada**: 4-6 semanas
**Dependencia**: Fase 1 completa.

---

## 2.1 Infraestructura DevOps

### 2.1.1 CI/CD con GitHub Actions

| Archivo | `.github/workflows/ci.yml` (crear) |
|---------|-------------------------------------|
| **Trigger** | `push` y `pull_request` a `main` |
| **Jobs**: | |
| | `lint`: `ruff check app/ tests/ quality/` |
| | `typecheck`: `mypy app/` |
| | `test`: `pytest --cov=app --cov-report=term --cov-report=xml` |
| | `quality`: `python -m quality.quality_agent --check-all` |
| | `security`: `detect-secrets` o similar |
| **Python** | 3.10+ |
| **Esfuerzo** | 3-4 horas |

### 2.1.2 Dockerizar dashboard Streamlit

| Archivo | `Dockerfile.dashboard` (crear), actualizar `docker-compose.yml` |
|---------|-----------------------------------------------------------------|
| **Qué** | Agregar servicio Streamlit similar a `Dockerfile.api` |
| **Por qué** | El dashboard es el punto de entrada principal del usuario. Debe ser desplegable junto con API y frontend. |
| **Esfuerzo** | 2-3 horas |

### 2.1.3 Migraciones versionadas con Alembic

| Archivos | `alembic.ini` (crear), `app/database/migrations.py` (refactor) |
|---------|---------------------------------------------------------------|
| **Qué** | Reemplazar el esquema actual de `CREATE TABLE IF NOT EXISTS` por migraciones versionadas con Alembic |
| **Por qué** | El esquema actual no permite: rollback, cambios incrementales, historia de migraciones, trabajo en equipo. Es crítico si el sistema escala. |
| **Cómo**: | |
| | 1) Inicializar Alembic: `alembic init alembic` dentro de `app/database/` |
| | 2) Crear migración inicial que refleje el schema actual (6 tablas) |
| | 3) Modificar `migrations.py` para ejecutar Alembic en vez de SQL directo |
| | 4) Crear tabla `alembic_version` automáticamente |
| **Esfuerzo** | 4-6 horas |

### 2.1.4 Logging estructurado con loguru

| Archivos | `app/config.py` (setup logging), todos los módulos que usan `print` o listas |
|---------|-----------------------------------------------------------------------------|
| **Qué** | Reemplazar `print()` y listas de log con `loguru` o `logging.getLogger(__name__)` estructurado |
| **Por qué** | Hoy el logging es inconsistente: algunos módulos usan listas (`self._log.append`), otros `print()`. No hay rotación, niveles, formato estructurado. |
| **Cómo**: | |
| | 1) Agregar `loguru` a requirements.txt (o usar `logging` estándar) |
| | 2) Crear `app/logging_setup.py` con configuración centralizada (archivo + consola, rotación diaria, formato JSON) |
| | 3) Reemplazar `print(f"info")` → `logger.info("info")` |
| | 4) Reemplazar listas de log → `logger.debug(...)` |
| **Esfuerzo** | 6-8 horas |

### 2.1.5 Singleton para load_settings()

| Archivo | `app/config.py` |
|---------|-----------------|
| **Qué** | Agregar `@functools.lru_cache(maxsize=1)` a `load_settings()` o implementar patrón singleton |
| **Por qué** | `load_settings()` se llama múltiples veces desde distintos módulos, parseando YAML cada vez. Un singleton cachea el resultado. |
| **Cómo** | Decorar `load_settings()` con `@functools.lru_cache(maxsize=1)`. Si es necesario forzar recarga, exponer `reload_settings()` que limpia el cache. |
| **Esfuerzo** | 1 hora |

---

## 2.2 Feature — Short Positions

### 2.2.1 Backtesting engine con soporte short

| Archivo | `app/backtesting/engine.py` |
|---------|-----------------------------|
| **Qué** | Modificar `_enter_position` y `_check_exit` para manejar posiciones cortas (`direction="SELL"`) |
| **Por qué** | Hoy el engine solo soporta long trades. Limita las estrategias que pueden generar señales short. |
| **Cómo**: | |
| | 1) `_enter_position`: si `direction="SELL"`, registrar posición con `qty` negativo, slippaje adverso es precio * (1 - slippage_pct) |
| | 2) `_check_exit`: para short, stop-loss = precio > entry (inverso), take-profit = precio < entry |
| | 3) PnL: para short, `(entry_price - exit_price) * quantity` |
| | 4) `TradeRecord` requiere un campo `direction` |
| **Esfuerzo** | 8-10 horas |

### 2.2.2 Exposure limits con shorts

| Archivo | `app/risk/exposure_limits.py` |
|---------|------------------------------|
| **Qué** | Agregar lógica de exposición para posiciones cortas (exposición negativa) |
| **Por qué** | La exposición de un short es diferente: no usa capital pero tiene riesgo ilimitado. |
| **Cómo** | Diferenciar entre exposición larga y corta. La exposición total debe ser `|long_exposure| + |short_exposure|`. |
| **Esfuerzo** | 3-4 horas |

### 2.2.3 VirtualPortfolio con shorts

| Archivo | `app/paper_trading/virtual_portfolio.py` |
|---------|------------------------------------------|
| **Qué** | Soportar `side="SELL"` (short) en métodos `buy`/`sell` |
| **Por qué** | Paper trading debe reflejar los mismos tipos de orden que backtesting. |
| **Cómo** | Posición corta: `quantity` negativo, entry_price, current_price. Unrealized PnL = `(entry_price - current_price) * abs(quantity)`. |
| **Esfuerzo** | 4-6 horas |

---

## 2.3 Feature — Trailing Stop + TP Dinámico

### 2.3.1 TrailingStop en risk module

| Archivo | `app/risk/stop_loss.py` (o nuevo `app/risk/trailing_stop.py`) |
|---------|---------------------------------------------------------------|
| **Qué** | Implementar trailing stop basado en ATR o porcentaje, que se actualiza a medida que el precio se mueve a favor |
| **Por qué** | Un trailing stop captura más ganancia en tendencias fuertes que un stop-loss fijo. |
| **Cómo** | `TrailingStop(activation_pct, trail_pct, atr_multiplier)`. En cada barra, si el precio sube (long), el stop se mueve hacia arriba. Nunca se mueve hacia abajo. |
| **Esfuerzo** | 6-8 horas |

### 2.3.2 Take-profit dinámico

| Archivo | `app/risk/stop_loss.py` (ampliar) |
|---------|------------------------------------|
| **Qué** | Calcular take-profit basado en ATR o en volatilidad reciente (no fijo) |
| **Por qué** | Un TP fijo no se adapta a condiciones de mercado. En mercados volátiles, un TP fijo puede dejar ganancias importantes. |
| **Cómo** | `take_profit_dynamic(entry_price, atr_value, multiplier=3)` → `entry_price + atr_value * multiplier` (long). Integrar con `RiskManager`. |
| **Esfuerzo** | 3-4 horas |

### 2.3.3 Integrar en RiskManager

| Archivo | `app/risk/risk_manager.py` |
|---------|----------------------------|
| **Qué** | Agregar `TrailingStop` y `take_profit_dynamic` como pasos opcionales en `evaluate()` |
| **Por qué** | Para que estrategias y backtesting se beneficien de estos features sin cambios adicionales. |
| **Esfuerzo** | 3-4 horas |

---

## 2.4 Refactor Data Layer

### 2.4.1 DAO layer para SQLite

| Archivos | `app/database/dao.py` (nuevo), refactor de todos los módulos que hacen SQL directo |
|---------|-----------------------------------------------------------------------------------|
| **Qué** | Crear clase `DataAccessObject` con métodos tipados: `save_candles()`, `get_candles()`, `save_prospect()`, `get_prospects()`, etc. |
| **Por qué** | Hoy el SQL está disperso en `market_data.py`, `prospecting/db.py`, `decision_log.py`, `paper_trading/storage.py`. Sin ORM, es difícil mantener consistencia. |
| **Cómo**: | |
| | 1) Crear `app/database/dao.py` con `class DataAccessObject` que recibe `db_path` |
| | 2) Implementar métodos uno por uno, comenzando por `candles` y `prospects` |
| | 3) Refactorizar los módulos existentes para usar DAO |
| | 4) Mantener la interfaz compatible durante la transición |
| **Esfuerzo** | 8-12 horas |

### 2.4.2 Connection context manager

| Archivo | `app/database/connection.py` |
|---------|------------------------------|
| **Qué** | Implementar `connection_scope()` como context manager que maneja commit/rollback |
| **Por qué** | Hoy las conexiones SQLite se abren y cierran manualmente. Si una operación falla a medias, quedan cambios parciales. |
| **Cómo** | `@contextmanager def connection_scope(db_path): conn = get_connection(db_path); try: yield conn; conn.commit(); except: conn.rollback(); raise; finally: conn.close()` |
| **Esfuerzo** | 2-3 horas |

### 2.4.3 Índices adicionales

| Archivo | `app/database/migrations.py` (o migración Alembic) |
|---------|-----------------------------------------------------|
| **Qué** | Agregar índices a `paper_trades.created_at`, `decision_log.timestamp`, `prospects.score` |
| **Por qué** | Estas columnas se usan frecuentemente en filtros/ordenamiento sin índice. |
| **Esfuerzo** | 1 hora |

### 2.4.4 Batching en store_klines

| Archivo | `app/data/market_data.py` |
|---------|---------------------------|
| **Qué** | Agrupar inserts en transacciones de 500-1000 filas en vez de INSERT por fila |
| **Por qué** | `executemany` es más rápido que inserts individuales, especialmente para descargas paginadas de 10k+ velas. |
| **Cómo** | `executemany` ya acepta lista de tuplas. Solo agrupar en chunks de 500 y ejecutar en un solo `conn.commit()`. |
| **Esfuerzo** | 2-3 horas |

---

## 2.5 Refactor Dashboard

### 2.5.1 Helpers compartidos (continuación de 1.8.1)

Ya iniciado en Fase 1, completar aquí con más funciones compartidas.

### 2.5.2 Cargar estrategias y parámetros desde config

| Archivos | `app/dashboard/pages/backtest.py`, `settings.yaml` |
|---------|---------------------------------------------------|
| **Qué** | Leer parámetros de estrategias desde `settings.yaml → strategies` en vez de tenerlos hardcodeados en el UI |
| **Por qué** | Hoy el backtest page solo configura MA crossover. Para RSI, Trend, etc., los parámetros están hardcodeados en cada estrategia. |
| **Cómo** | 1) Leer `config.strategies` en backtest page. 2) Renderizar inputs dinámicamente según la estrategia seleccionada. 3) Pasar parámetros al crear la instancia. |
| **Esfuerzo** | 6-8 horas |

### 2.5.3 Error boundary para imports de páginas

| Archivo | `app/dashboard/main.py` |
|---------|-------------------------|
| **Qué** | Reemplazar `__import__(page_module, fromlist=["render"])` dinámico por import explícito con try/except |
| **Por qué** | Si una página tiene un error de import, todo el dashboard crashea. Con import explícito, podemos mostrar un mensaje de error. |
| **Cómo** | `try: import app.dashboard.pages.overview as overview_page; except ImportError as e: st.error(f"Error cargando página: {e}")` |
| **Esfuerzo** | 3-4 horas |

### 2.5.4 Tests para dashboard

| Archivo test | `tests/test_dashboard_*.py` |
|--------------|----------------------------|
| **Qué** | Agregar tests unitarios para las funciones helper y páginas |
| **Por qué** | Dashboard tiene 0 cobertura de tests. Las páginas tienen lógica de negocio (cálculos, filtros). |
| **Cómo** | Testear funciones helper (cálculos de portfolio, procesamiento de datos) sin Streamlit. Usar `st.testing.v1` de Streamlit si está disponible. |
| **Esfuerzo** | 6-8 horas |

---

## 2.6 Property-Based Testing

| Archivo test | `tests/test_risk_position_sizing_property.py`, etc. |
|--------------|------------------------------------------------------|
| **Librería** | `hypothesis` |
| **Qué**: | |
| | `position_sizing`: para cualquier capital > 0, entry_price > 0, stop_loss < entry_price: `position_value <= capital * max_position_pct` |
| | `stop_loss.fixed_percentage`: stop_price siempre está entre `entry * (1 - max_stop_pct)` y `entry * (1 - min_stop_pct)` |
| | `exposure_limits`: post-trade exposure siempre <= `max_asset_pct * capital` |
| | `circuit_breakers`: tras N pérdidas consecutivas > `max_consecutive_losses`, trading bloqueado |
| **Esfuerzo** | 4-6 horas |

---

## 2.7 Frontend Next.js

| Archivos | `frontend/` completo |
|---------|----------------------|
| **Estado validado** | Parcialmente implementado. Varias paginas ya consumen FastAPI real mediante `frontend/src/lib/api.ts`. |
| **Qué** | Completar las paginas faltantes, alinear tipos TypeScript con respuestas reales y consolidar UX/error handling. |
| **Por qué**: | |
| | El frontend ya tiene estructura funcional, pero aun faltan paginas y tipos compartidos. |
| | Algunas acciones POST usan `fetch()` directo en componentes en vez de un cliente API unificado. |
| | No existe estado global formal para configuracion/portfolio. |
| **Paginas ya implementadas**: | |
| | `overview/` -> `GET /api/v1/config`, `GET /api/v1/market/summary` |
| | `market/` -> `GET /api/v1/market/price/{symbol}`, `GET /api/v1/market/candles/{symbol}/{interval}` |
| | `portfolio/` -> `GET /api/v1/portfolio/state`, `/trades`, `/snapshots` |
| | `prospects/` -> `GET /api/v1/prospecting/ranking`, acciones de prospecting |
| | `backtest/` -> `GET /api/v1/backtest/strategies`, `POST /api/v1/backtest/run` |
| | `decisions/` -> `GET /api/v1/decisions` |
| | `risk/` -> `GET /api/v1/risk/limits`, `POST /api/v1/risk/evaluate` |
| | `alerts/` -> `GET /api/v1/alerts/history`, `GET /api/v1/alerts/rules` |
| | `ranking/` -> `GET /api/v1/prospecting/ranking` |
| **Paginas pendientes**: | |
| | `assets/[symbol]/` detalle de activo |
| | `journal/` analisis de journal |
| | `logs/` visor de logs |
| **Pendientes tecnicos**: | |
| | Crear `frontend/src/types/` para tipos compartidos. |
| | Agregar helper POST/PUT/DELETE en `frontend/src/lib/api.ts`. |
| | Revisar responsive design. |
| | Mejorar loading/error states consistentes. |
| | Auth JWT queda como feature futura, no requisito de Fase 2 inmediata para sistema interno. |
| **Esfuerzo** | 2-3 semanas |

---

## 2.8 Features Avanzadas

### 2.8.1 Walk-forward optimization

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/backtesting/optimizer.py` (nuevo) |
| **Qué** | Implementar optimización walk-forward: entrenar estrategia en ventana de entrenamiento, testear en ventana de testeo, deslizar |
| **Por qué** | Reduce overfitting vs optimización simple. Es el estándar de la industria. |
| **Cómo** | Dividir datos en N ventanas (ej: 70% train, 30% test). Para cada ventana, optimizar parámetros en train, evaluar en test. Promediar resultados. |
| **Esfuerzo** | 8-12 horas |

### 2.8.2 Monte Carlo simulation

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/backtesting/monte_carlo.py` (nuevo) |
| **Qué** | Simular N caminos aleatorios de rendimientos basados en la distribución de trades del backtest |
| **Por qué** | Muestra la distribución de resultados posibles, no solo un número puntual. Ayuda a evaluar la robustez de una estrategia. |
| **Cómo** | 1) Tomar la lista de PnL% de trades del backtest. 2) Samplear con reemplazo N veces (ej: 1000). 3) Calcular equity curve para cada sampleo. 4) Reportar percentiles 5/50/95 de ROI final, drawdown máximo, Sharpe. |
| **Esfuerzo** | 6-8 horas |

### 2.8.3 AI module expansion

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/ai/` (ampliar) |
| **Qué**: | |
| | Clasificador de régimen de mercado: trending alcista/bajista, ranging, volátil |
| | Predicción de volatilidad a corto plazo (modelo GARCH o similar simple) |
| | Detección de patrones de velas (doji, hammer, engulfing) |
| **Por qué** | El módulo AI actual es liviano (3 archivos). Puede diferenciar el producto. |
| **Esfuerzo** | 12-16 horas |

### 2.8.4 Sistema de plugins de estrategias

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/strategies/plugin_loader.py` (nuevo) |
| **Qué** | Permitir cargar estrategias personalizadas desde archivos .py externos (no modificar el código base) |
| **Por qué** | Usuarios avanzados querrán probar sus propias estrategias sin mergear código al repositorio principal. |
| **Cómo** | 1) Definir interfaz `StrategyPlugin(BaseStrategy)`. 2) `PluginLoader` escanea `strategies_plugins/` directory. 3) Importa dinámicamente clases que extienden `BaseStrategy`. 4) Registra en el sistema de backtesting y paper trading. |
| **Esfuerzo** | 8-12 horas |

### 2.8.5 API pública documentada

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/api/` |
| **Qué** | Pulir los endpoints existentes, agregar documentación OpenAPI completa, versionado de API |
| **Por qué** | FastAPI ya genera Swagger UI en `/docs`. Solo falta asegurar que todos los endpoints tengan docstrings, response models, y error handling consistente. |
| **Cómo** | 1) Revisar cada router. 2) Agregar `response_model` a todos los endpoints. 3) Documentar parámetros con `Query(description=...)`. 4) Agregar tags para agrupar endpoints. 5) Implementar versionado (`/api/v1/...`). |
| **Esfuerzo** | 6-8 horas |

### 2.8.6 Multi-usuario

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/api/auth.py` (nuevo), `app/database/users.py` (nuevo) |
| **Qué** | Agregar autenticación JWT con usuarios y sesiones aisladas |
| **Por qué** | Si el producto se expone vía web (Next.js), múltiples usuarios pueden querer acceder con sus propias configuraciones. |
| **Cómo** | 1) Tabla `users` en SQLite. 2) Endpoint `/api/v1/auth/login` que retorna JWT. 3) Dependencia FastAPI `get_current_user()` para rutas protegidas. 4) Scope de datos por usuario (cada usuario ve su portfolio, trades, config). |
| **Esfuerzo** | 12-16 horas |

### 2.8.7 Export PDF

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/reporting/pdf_generator.py` (nuevo) |
| **Qué** | Generar reportes PDF a partir de resultados de backtesting y resúmenes de portfolio |
| **Por qué** | Complementa la exportación JSON/CSV existente para presentación a stakeholders o registro personal. |
| **Cómo** | Usar `weasyprint`, `reportlab`, o `fpdf2`. Tomar métricas del backtest, equity curve (como tabla de números), lista de trades, y generar PDF con formato profesional. |
| **Esfuerzo** | 6-8 horas |

---

## Resumen de Esfuerzo Total

| Fase | Estimación |
|------|-----------|
| **Fase 1** | 3-4 semanas (80-100 horas) |
| **Fase 2** | 5-7 semanas (130-170 horas) |
| **Total** | 8-11 semanas (210-270 horas) |

**Nota**: Las estimaciones asumen un desarrollador con conocimiento del codebase. Son tiempos netos de desarrollo, sin contar revisiones ni imprevistos.

## Checklist de Progreso

Se recomienda mantener este checklist actualizado a medida que se completan las tareas:

### Fase 1
- [x] 1.1.1 Safety checks attribute name
- [x] 1.1.2 Circuit breakers loss limits
- [x] 1.1.3 Missing return en simulator (validado como ya corregido)
- [x] 1.1.4 DCA double adjustment
- [x] 1.1.5 Dashboard prices BTC bug
- [x] 1.1.6 Timestamp extraction (5 archivos)
- [x] 1.1.7 Ranking missing import
- [x] 1.2.1 Centralizar credenciales Binance
- [x] 1.2.2 Telegram token security
- [x] 1.3.1 Tests circuit_breakers
- [ ] 1.3.2 Tests risk_manager
- [x] 1.3.3 Tests config
- [x] 1.3.4 Tests metrics
- [x] 1.3.5 Tests binance_client
- [x] 1.3.6 Tests migrations
- [x] 1.4.1 Eliminar stubs test_app_*
- [x] 1.4.2 Renombrar tests
- [x] 1.4.3 Activar validate_unused_imports
- [x] 1.4.4 Implementar fail_fast
- [x] 1.4.5 TestValidator falle realmente
- [x] 1.4.6 Integrar ruff + mypy en quality agent
- [ ] 1.5.1 Vectorizar estrategias (5 archivos)
- [ ] 1.5.2 Stop loss/take profit configurable
- [ ] 1.5.3 Confidence/risk_score parametrizable
- [ ] 1.5.4 Chequeo minimum_bars
- [ ] 1.5.5 Unificar representación porcentajes
- [ ] 1.6.1 VirtualPortfolio timestamp simulación
- [ ] 1.6.2 Registrar buys en circuit breakers
- [ ] 1.6.3 Sincronizar VirtualOrderManager + storage
- [ ] 1.7 Integrar Risk Manager en backtesting
- [ ] 1.8.1 Eliminar duplicación helpers
- [ ] 1.8.2 Unificar capital inicial dinámico
- [ ] 1.8.3 Manejo de errores consistente

### Fase 2
- [ ] 2.1.1 CI/CD GitHub Actions
- [ ] 2.1.2 Dockerizar dashboard
- [ ] 2.1.3 Migraciones Alembic
- [ ] 2.1.4 Logging estructurado
- [ ] 2.1.5 Singleton load_settings
- [ ] 2.2.1 Backtesting con shorts
- [ ] 2.2.2 Exposure limits con shorts
- [ ] 2.2.3 VirtualPortfolio con shorts
- [ ] 2.3.1 Trailing stop
- [ ] 2.3.2 Take-profit dinámico
- [ ] 2.3.3 Integrar en RiskManager
- [ ] 2.4.1 DAO layer
- [ ] 2.4.2 Connection context manager
- [ ] 2.4.3 Índices adicionales
- [ ] 2.4.4 Batching store_klines
- [ ] 2.5.1 Helpers dashboard (cont. 1.8.1)
- [ ] 2.5.2 Estrategias desde config
- [ ] 2.5.3 Error boundary imports
- [ ] 2.5.4 Tests dashboard
- [ ] 2.6 Property-based tests
- [ ] 2.7 Frontend Next.js completo
- [ ] 2.8.1 Walk-forward optimization
- [ ] 2.8.2 Monte Carlo simulation
- [ ] 2.8.3 AI module expansion
- [ ] 2.8.4 Sistema de plugins estrategias
- [ ] 2.8.5 API pública documentada
- [ ] 2.8.6 Multi-usuario auth
- [ ] 2.8.7 Export PDF
