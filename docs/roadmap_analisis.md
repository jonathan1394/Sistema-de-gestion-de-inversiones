# Roadmap: Analisis de Mercados e Inversiones - CriptoLab

## Estado Actual

El proyecto cuenta con los siguientes modulos funcionales:

| Modulo | Estado | Archivos Principales |
|--------|--------|---------------------|
| Datos historicos | Completo | `app/data/market_data.py`, `app/data/binance_client.py` |
| Base de datos | Completo | `app/database/connection.py`, `app/database/models.py` |
| Backtesting | Completo | `app/backtesting/engine.py`, `app/backtesting/metrics.py` |
| Estrategias | Funcional | `app/strategies/moving_average.py`, `rsi_strategy.py`, `trend_following.py`, `dca_dynamic.py`, `rebalance.py` |
| Risk management | Completo | `app/risk/risk_manager.py`, `stop_loss.py`, `position_sizing.py`, `exposure_limits.py`, `circuit_breakers.py` |
| Prospeccion/Scoring | Funcional | `app/prospecting/screener.py`, `app/prospecting/scoring.py` |
| Resumen de mercado | Funcional | `app/ai/market_summary.py` |
| Explicacion de senales | Funcional | `app/ai/signal_explainer.py` |
| Journal de trading | Funcional | `app/ai/journal_analyzer.py` |
| Paper trading | Funcional | `app/paper_trading/simulator.py`, `virtual_portfolio.py` |
| Alertas | Funcional | `app/alerts/engine.py`, `app/alerts/channels.py` |
| Dashboard (Streamlit) | Completo | `app/dashboard/main.py` + todas las paginas en `app/dashboard/pages/` |
| Ejecucion/Seguridad | Completo | `app/execution/safety_checks.py`, `order_manager.py` |
| Sistema de calidad | Completo | `quality/` con gates y validadores |

### Estado de Implementación del Roadmap

La mayoría de los elementos del roadmap original han sido implementados:

✅ **Prospectos visibles en menu** - Integrado en `app/dashboard/main.py`  
✅ **Pesos de scoring configurables** - Leídos de `settings.yaml` en `app/prospecting/scoring.py`  
✅ **Persistencia de paper trading** - Implementada con tablas `paper_trades` y `paper_portfolio`  
✅ **Vista de analisis de mercado** - `app/dashboard/pages/market_analysis.py` existe y funciona  
✅ **Ranking automatico de activos** - Implementado en el flujo de `app/prospecting/screener.py` y visualizado en `app/dashboard/pages/prospects.py`  
✅ **Sistema de recomendación "Invertir/Vigilar/Evitar"** - Implementado con umbrales configurables  
✅ **Comparación multi-timeframe** - Integrada en el análisis de mercado  
✅ **Persistencia de operaciones paper** - Guardadas en SQLite vía `app/paper_trading/storage.py`

Algunos elementos avanzados están en progreso o planificados para fases futuras.

---

## Fase 1: Visibilidad y Fundamentos (Semanas 1-2)

### 1.1 Integrar Prospectos en Dashboard

**Objetivo**: Hacer accesible la prospeccion desde la interfaz principal.

**Acciones**:
- Agregar `"Prospects": "app.dashboard.pages.prospects"` al diccionario `PAGES` en `app/dashboard/main.py`.
- Verificar que la pagina renderiza correctamente con la navegacion existente.
- Agregar boton "Run Screener" para ejecutar analisis sobre todos los prospectos.

**Archivos a modificar**:
- `app/dashboard/main.py`
- `app/dashboard/pages/prospects.py`

**Criterio de aceptacion**:
- El menu lateral muestra "Prospects".
- Se puede agregar/eliminar/promover activos.
- El boton "Run Screener" actualiza los scores.

---

### 1.2 Conectar Scoring con Configuracion

**Objetivo**: Usar los pesos de `settings.yaml` en vez de valores fijos.

**Acciones**:
- Modificar `app/prospecting/scoring.py` para recibir pesos como parametro.
- Actualizar `app/prospecting/screener.py` para pasar `settings.prospecting.scoring_weights`.
- Agregar validacion de que los pesos suman 1.0.

**Archivos a modificar**:
- `app/prospecting/scoring.py`
- `app/prospecting/screener.py`

**Configuracion existente en `settings.yaml`**:
```yaml
prospecting:
  scoring_weights:
    trend: 0.30
    volatility: 0.10
    volume: 0.15
    rsi: 0.15
    return_: 0.15
    signals: 0.15
```

**Criterio de aceptacion**:
- Los pesos se leen de `settings.yaml`.
- Se puede ajustar el peso de cada factor sin cambiar codigo.
- Se valida que los pesos suman 1.0.

---

### 1.3 Persistir Operaciones Paper en SQLite

**Objetivo**: No perder el historial de paper trading al cerrar sesion.

**Acciones**:
- Crear tabla `paper_trades` en `app/database/models.py`:
  ```sql
  CREATE TABLE IF NOT EXISTS paper_trades (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      interval TEXT NOT NULL,
      action TEXT NOT NULL,
      quantity REAL NOT NULL,
      price REAL NOT NULL,
      commission REAL DEFAULT 0.0,
      pnl REAL DEFAULT 0.0,
      pnl_pct REAL DEFAULT 0.0,
      reason TEXT,
      created_at TEXT NOT NULL
  );
  ```
- Crear tabla `paper_portfolio`:
  ```sql
  CREATE TABLE IF NOT EXISTS paper_portfolio (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      quantity REAL NOT NULL,
      entry_price REAL NOT NULL,
      current_price REAL NOT NULL,
      unrealized_pnl REAL DEFAULT 0.0,
      entry_time TEXT NOT NULL,
      updated_at TEXT NOT NULL
  );
  ```
- Crear modulo `app/paper_trading/storage.py` con funciones CRUD.
- Modificar `app/dashboard/pages/portfolio.py` para leer/guardar en SQLite.
- Crear migracion en `app/database/migrations.py`.

**Archivos a crear/modificar**:
- `app/paper_trading/storage.py` (nuevo)
- `app/database/models.py`
- `app/database/migrations.py`
- `app/dashboard/pages/portfolio.py`

**Criterio de aceptacion**:
- Al cerrar y abrir Streamlit, las posiciones y trades se mantienen.
- Se puede consultar historial de trades paper.
- Las metricas (win rate, PnL, etc.) se calculan sobre datos reales persistidos.

---

## Fase 2: Analisis de Mercado (Semanas 3-4)

### 2.1 Pagina de Analisis de Mercado

**Objetivo**: Vista dedicada para analizar un activo en profundidad.

**Acciones**:
- Crear `app/dashboard/pages/market_analysis.py`.
- Usar `generate_market_summary()` de `app/ai/market_summary.py`.
- Mostrar:
  - Precio actual, cambio 24h, cambio 7d.
  - Tendencia actual (strong_up, up, sideways, down, strong_down).
  - RSI con zona (sobrecompra/sobreventa).
  - Volatilidad (baja/moderada/alta).
  - Volumen relativo (alto/normal/bajo).
  - Soporte y resistencia.
  - EMAs 20 y 50.
  - Resumen textual del mercado.
- Agregar selector de timeframe (1h, 4h, 1d).
- Agregar boton "Refresh" para recalcular.

**Archivos a crear**:
- `app/dashboard/pages/market_analysis.py`

**Criterio de aceptacion**:
- Se puede seleccionar activo y timeframe.
- Se muestra resumen completo del mercado.
- Los niveles clave se actualizan con los datos mas recientes.

---

### 2.2 Matriz Multi-Timeframe

**Objetivo**: Comparar la lectura de mercado en multiples temporalidades.

**Acciones**:
- Crear funcion `analyze_multi_timeframe()` que ejecute `generate_market_summary()` para 1h, 4h y 1d.
- Construir tabla comparativa:
  ```
  Activo    | 1h        | 4h        | 1d        | Confluencia
  --------- | --------- | --------- | --------- | -----------
  BTCUSDT   | up        | strong_up | up        | 3/3 alcista
  ETHUSDT   | sideways  | up        | up        | 2/3 alcista
  SOLUSDT   | down      | sideways  | up        | 1/3 alcista
  ```
- Calcular score de confluencia (0-3).
- Integrar en pagina de analisis de mercado.

**Archivos a modificar**:
- `app/dashboard/pages/market_analysis.py`
- `app/ai/market_summary.py` (posible funcion wrapper)

**Criterio de aceptacion**:
- Se muestra tabla con analisis por timeframe.
- La confluencia se calcula automaticamente.
- Se identifican divergencias entre timeframes.

---

### 2.3 Ranking Automatico de Activos

**Objetivo**: Ranking periodico de activos ordenados por potencial de inversion.

**Acciones**:
- Crear `app/prospecting/ranking.py`:
  ```python
  @dataclass
  class AssetRanking:
      symbol: str
      score: float
      recommendation: str  # "INVERTIR", "VIGILAR", "NEUTRAL", "EVITAR"
      trend: str
      confluence: int
      sharpe_best: float
      last_signal: str

  def generate_ranking(screener_result, backtest_results) -> list[AssetRanking]:
      ...
  ```
- Crear tabla `asset_rankings` en SQLite para persistir rankings historicos.
- Mostrar ranking en dashboard con filtros.

**Archivos a crear**:
- `app/prospecting/ranking.py`
- `app/dashboard/pages/ranking.py` (nuevo)

**Criterio de aceptacion**:
- Se genera ranking de todos los activos en prospeccion.
- Cada activo tiene recomendacion clara.
- Se puede comparar ranking actual con el anterior.

---

### 2.4 Sistema de Recomendacion "Invertir / Vigilar / Evitar"

**Objetivo**: Convertir el score numerico en una accion concreta.

**Acciones**:
- Definir umbrales en `settings.yaml`:
  ```yaml
  prospecting:
    recommendation:
      invertir: 0.75
      vigilat: 0.60
      neutral: 0.40
      evitar: 0.0
  ```
- Crear funcion `get_recommendation(score, confluence)`:
  - `score >= 0.75` y `confluence >= 2`: **INVERTIR** (candidato fuerte)
  - `score >= 0.60` y `confluence >= 1`: **VIGILAR** (esperar mejor entrada)
  - `score >= 0.40`: **NEUTRAL** (no acciones por ahora)
  - `score < 0.40`: **EVITAR** (señales debiles)
- Mostrar recomendacion con color en dashboard (verde/amarillo/gris/rojo).

**Archivos a modificar**:
- `app/prospecting/scoring.py`
- `app/dashboard/pages/prospects.py`
- `settings.yaml`

**Criterio de aceptacion**:
- Cada activo muestra recomendacion con color.
- Los umbrales son configurables.
- La recomendacion considera tanto score como confluencia de timeframes.

---

## Fase 3: Backtesting Comparativo (Semanas 5-6)

### 3.1 Backtesting Multi-Estrategia

**Objetivo**: Probar todas las estrategias automaticamente sobre un activo.

**Acciones**:
- Crear `app/backtesting/comparator.py`:
  ```python
  @dataclass
  class BacktestComparison:
      symbol: str
      interval: str
      results: list[StrategyMetrics]
      best_strategy: str
      best_sharpe: float

  def compare_strategies(data, symbol, strategies, capital) -> BacktestComparison:
      ...
  ```
- Crear script `scripts/compare_strategies.py` para ejecucion batch.
- Integrar en dashboard con boton "Compare All Strategies".

**Archivos a crear**:
- `app/backtesting/comparator.py`
- `scripts/compare_strategies.py`

**Criterio de aceptacion**:
- Se ejecutan MA, RSI, Trend Following, DCA y Rebalance sobre el mismo activo.
- Se muestra tabla comparativa con Sharpe, drawdown, profit factor, ROI.
- Se identifica la mejor estrategia automaticamente.

---

### 3.2 Backtesting Multi-Activo y Multi-Timeframe

**Objetivo**: Evaluar estrategias cruzando activos y temporalidades.

**Acciones**:
- Crear script `scripts/compare_strategies.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --intervals 1h,4h,1d`.
- Generar ranking consolidado:
  ```
  Rank | Activo    | TF   | Estrategia | Sharpe | DD%    | PF   | ROI%
  ---- | --------- | ---- | ---------- | ------ | ------ | ---- | -----
  1    | BTCUSDT   | 4h   | Trend      | 1.85   | -12.3  | 1.92 | +45.2
  2    | ETHUSDT   | 1d   | MA Cross   | 1.62   | -15.1  | 1.78 | +38.7
  3    | SOLUSDT   | 4h   | RSI        | 1.41   | -18.5  | 1.55 | +31.4
  ```
- Exportar ranking a JSON y CSV.

**Archivos a modificar**:
- `scripts/compare_strategies.py`

**Criterio de aceptacion**:
- Se puede ejecutar comparacion completa con un solo comando.
- Se genera ranking exportable.
- Se respetan los filtros minimos (50 trades, Sharpe > 1, PF > 1.2).

---

### 3.3 Ficha Completa por Activo

**Objetivo**: Vista unificada con todo lo relevante de un activo.

**Acciones**:
- Crear `app/dashboard/pages/asset_detail.py`:
  - Precio actual y cambio.
  - Score de prospeccion.
  - Recomendacion (Invertir/Vigilar/Evitar).
  - Analisis de mercado (trend, RSI, volatilidad).
  - Multi-timeframe confluencia.
  - Mejor estrategia historica (Sharpe, PF, ROI).
  - Senales recientes.
  - Niveles clave (soporte/resistencia/EMA).
  - Riesgo estimado.

**Archivos a crear**:
- `app/dashboard/pages/asset_detail.py`

**Criterio de aceptacion**:
- Desde el ranking se puede hacer click y ver ficha completa.
- La ficha muestra informacion consolidada de todos los modulos.
- Se puede exportar la ficha como PDF o Markdown.

---

## Fase 4: Portfolio y Diario (Semanas 7-8)

### 4.1 Portfolio Persistente con Metricas

**Objetivo**: Metricas de cartera calculadas sobre datos reales.

**Acciones**:
- Crear `app/paper_trading/metrics.py`:
  - Win rate historico.
  - Profit factor.
  - Sharpe ratio del portfolio.
  - Max drawdown historico.
  - Distribucion por activo.
  - Exposicion total y por altcoin.
  - Comparacion contra benchmark (BTC).
- Mostrar metricas en pagina de Portfolio.

**Archivos a crear**:
- `app/paper_trading/metrics.py`

**Criterio de aceptacion**:
- Las metricas se calculan sobre trades persistidos.
- Se puede comparar rendimiento contra BTC.
- Se muestran graficos de distribucion y exposicion.

---

### 4.2 Diario de Trading

**Objetivo**: Analizar comportamiento del trader y mejorar decisiones.

**Acciones**:
- Crear `app/dashboard/pages/journal.py`:
  - Subir archivo JSON de trades.
  - Ejecutar `generate_journal_report()`.
  - Mostrar:
    - Win rate y profit factor.
    - Ganancia/perdida promedio.
    - Perdidas consecutivas maximas.
    - Flags de comportamiento (revenge trading, martingala, cierre temprano).
    - Sugerencias de mejora.
  - Guardar analisis historico en SQLite.
- Crear tabla `journal_analyses` para persistir reportes.

**Archivos a crear**:
- `app/dashboard/pages/journal.py`
- `app/database/models.py` (agregar tabla)

**Criterio de aceptacion**:
- Se puede subir historial de trades.
- Se muestran flags de comportamiento problematico.
- Se guardan analisis para comparar evolucion.

---

### 4.3 Alertas Mejoradas

**Objetivo**: Alertas accionables basadas en analisis de mercado.

**Acciones**:
- Agregar reglas en `app/alerts/engine.py`:
  - Activo supera score minimo para inversion.
  - RSI entra en sobreventa con tendencia alcista.
  - Precio cruza EMA 200.
  - Drawdown de cartera supera limite configurado.
  - Senial BUY/SELL confirmada por 2+ estrategias.
  - Confluencia multi-timeframe alcanzada.
- Agregar canal Telegram (ya existe soporte en `settings.yaml`).
- Crear resumen diario automatico.

**Archivos a modificar**:
- `app/alerts/engine.py`
- `app/alerts/channels.py`

**Criterio de aceptacion**:
- Las alertas se disparan por reglas configurables.
- Se pueden enviar por Telegram.
- El resumen diario incluye ranking y posiciones.

---

## Fase 5: Reportes y Exportacion (Semanas 9-10)

### 5.1 Reporte Diario Automatizado

**Objetivo**: Generar reporte completo del mercado y cartera cada dia.

**Acciones**:
- Crear `scripts/daily_report.py`:
  - Ranking actualizado de activos.
  - Analisis multi-timeframe de principales activos.
  - Estado de cartera paper.
  - Senales activas.
  - Alertas del dia.
  - Sugerencias de accion.
- Exportar a Markdown y JSON.
- Enviar por Telegram si esta configurado.

**Archivos a crear**:
- `scripts/daily_report.py`

**Criterio de aceptacion**:
- El reporte se genera con un solo comando.
- Incluye toda la informacion relevante.
- Se puede programar con cron.

---

### 5.2 Dashboard Completo

**Objetivo**: Menu de navegacion completo con todas las funcionalidades.

**Acciones**:
- Actualizar `app/dashboard/main.py` con todas las paginas:
  ```python
  PAGES = {
      "Overview": "app.dashboard.pages.overview",
      "Market Analysis": "app.dashboard.pages.market_analysis",
      "Ranking": "app.dashboard.pages.ranking",
      "Asset Detail": "app.dashboard.pages.asset_detail",
      "Prospects": "app.dashboard.pages.prospects",
      "Backtesting": "app.dashboard.pages.backtest",
      "Portfolio": "app.dashboard.pages.portfolio",
      "Journal": "app.dashboard.pages.journal",
      "Risk": "app.dashboard.pages.risk",
      "Alerts": "app.dashboard.pages.alerts",
      "Logs": "app.dashboard.pages.logs",
  }
  ```
- Agregar iconos a cada pagina.
- Mejorar navegacion con sidebar mejorado.

**Archivos a modificar**:
- `app/dashboard/main.py`

**Criterio de aceptacion**:
- Todas las paginas son accesibles desde el menu.
- La navegacion es intuitiva.
- No hay paginas huérfanas.

---

## Resumen de Entregables por Fase

| Fase | Semanas | Entregables Principales |
|------|---------|------------------------|
| 1 | 1-2 | Prospectos en menu, scoring configurable, portfolio persistente |
| 2 | 3-4 | Pagina analisis de mercado, matriz multi-timeframe, ranking, recomendaciones |
| 3 | 5-6 | Backtesting comparativo multi-estrategia/activo/TF, ficha por activo |
| 4 | 7-8 | Metricas de portfolio, diario de trading, alertas mejoradas |
| 5 | 9-10 | Reporte diario automatizado, dashboard completo |

---

## Prioridad de Implementacion

### Alta (Hacer primero)
1. Integrar Prospectos en dashboard.
2. Conectar scoring con configuracion.
3. Persistir portfolio paper en SQLite.
4. Crear pagina de analisis de mercado.
5. Sistema de recomendacion Invertir/Vigilar/Evitar.

### Media (Hacer despues)
6. Matriz multi-timeframe.
7. Ranking automatico de activos.
8. Backtesting comparativo.
9. Ficha completa por activo.
10. Diario de trading.

### Baja (Hacer al final)
11. Alertas por Telegram.
12. Reporte diario automatizado.
13. Dashboard completo con iconos.
14. Exportacion a PDF/Markdown.

---

## Metricas de Exito

| Metrica | Target |
|---------|--------|
| Activos analizados automaticamente | >= 10 |
| Timeframes comparados por activo | 3 (1h, 4h, 1d) |
| Estrategias comparadas por activo | 5 (MA, RSI, Trend, DCA, Rebalance) |
| Trades paper persistidos | 100% |
| Alertas configurables | >= 6 reglas |
| Tiempo para generar ranking completo | < 30 segundos |
| Reporte diario generado | Automatico con cron |

---

## Dependencias Tecnicas

### Modulos Existentes a Reutilizar
- `app/ai/market_summary.py` -> analisis de mercado
- `app/prospecting/screener.py` -> screener de activos
- `app/prospecting/scoring.py` -> scoring (necesita refactor)
- `app/backtesting/engine.py` -> backtesting
- `app/ai/journal_analyzer.py` -> diario de trading
- `app/alerts/engine.py` -> alertas
- `app/risk/exposure_limits.py` -> limites de exposicion

### Nuevos Modulos a Crear
- `app/prospecting/ranking.py`
- `app/backtesting/comparator.py`
- `app/paper_trading/storage.py`
- `app/paper_trading/metrics.py`
- `app/dashboard/pages/market_analysis.py`
- `app/dashboard/pages/ranking.py`
- `app/dashboard/pages/asset_detail.py`
- `app/dashboard/pages/journal.py`
- `scripts/daily_report.py`
- `scripts/compare_strategies.py`

---

## Notas de Implementacion

- Todos los timestamps en UTC milisegundos.
- Backtests deben modelar comisiones (0.1%) y slippage (0.1%).
- Estrategias necesitan >= 50 trades, PF > 1.2, Sharpe > 1 para promocion.
- Position sizing basado en risk %, no cantidades fijas.
- No futuros/leverage en version inicial.
- Nunca commitear `.env`, `config/secrets.env`, `*.db`, o `reports/agent_logs/`.
- Correr `python -m quality.quality_agent --check-all` antes de cada commit.
