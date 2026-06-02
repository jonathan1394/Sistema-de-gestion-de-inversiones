# CriptoLab

Sistema privado de inversión cripto enfocado en disciplina, gestión de riesgo y validación sistemática de estrategias.

## Características principales

- Descarga de datos históricos desde Binance REST
- Almacenamiento en SQLite con validación de continuidad
- Backtesting de múltiples estrategias con modelado de comisiones y slippage
- Sistema de gestión de riesgo (tamaño de posición, stop-loss, límites de exposición)
- Paper trading con persistencia en base de datos
- Dashboard interactivo con Streamlit para análisis y monitoreo
- Sistema de prospección y scoring de activos
- Sistema de alertas configurables con detección de drawdown
- Diario de trading para análisis de comportamiento
- Sistema de calidad automatizado con gates y validadores
- Motor de decisiones para operaciones paper con registro de trazabilidad
- Sistema de ranking multi-timeframe y confluencia
- Generador de reportes diarios con envío opcional por Telegram

## Arquitectura

El proyecto sigue una arquitectura modular bajo el directorio `app/`:

- `app/data`: Cliente Binance y manejo de datos de mercado
- `app/database`: Conexión SQLite y migraciones
- `app/strategies`: Implementación de estrategias (MA, RSI, Trend Following, DCA, Rebalance)
- `app/backtesting`: Motor de backtesting y cálculo de métricas
- `app/risk`: Gestión de riesgo (circuit breakers, stop loss, position sizing, exposure limits)
- `app/paper_trading`: Simulador de trading y almacenamiento persistente
- `app/execution`: Gestión de órdenes y verificaciones de seguridad
- `app/alerts`: Sistema de alertas y notificaciones
- `app/ai`: Análisis de mercado, explicación de señales y análisis de diario
- `app/prospecting`: Screening y scoring de activos
- `app/dashboard`: Interfaz Streamlit con múltiples páginas
- `app/config`: Carga de configuración desde settings.yaml y variables de entorno

## Configuración

La configuración se gestiona mediante `settings.yaml` en la raíz del proyecto, con overridas mediante variables de entorno:

- `APP_MODE`: analysis, backtest, paper, real_manual, real_auto_limited
- `KILL_SWITCH`: true/false para bloquear nuevas operaciones
- `DATABASE_PATH`: ruta personalizada para la base de datos SQLite

Variables de entorno requeridas (ver `secrets.example.env`):
- API keys de Binance (solo lectura recomendado para fases iniciales)
- Configuración de notificaciones (Telegram, etc.)

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

### Descargar datos históricos

```bash
# Descarga básica
python -m scripts.download_historical --symbol BTCUSDT --interval 1h --limit 1000

# Con rango temporal específico (milisegundos UTC)
python -m scripts.download_historical --symbol ETHUSDT --interval 4h --start-ms 1704067200000 --end-ms 1711929600000

# Descarga paginada para rangos extensos
python -m scripts.download_historical --symbol BTCUSDT --interval 1h --start-ms 1672531200000 --end-ms 1704067200000 --paginate --max-batches 200
```

### Backtesting

```bash
# Backtest simple de cruce de medias móviles
python -m scripts.run_backtest_ma --symbol BTCUSDT --interval 1h --start-ms 1704067200000 --end-ms 1711929600000 --fast 20 --slow 50 --capital 1000

# Con exportación de resultados
python -m scripts.run_backtest_ma --symbol BTCUSDT --interval 1h --start-ms 1704067200000 --end-ms 1711929600000 --export-dir ./reports/backtests/btc_1h_ma

# Ejecutar backtest personalizado
python -m scripts.run_backtest --symbol BTCUSDT --interval 1h --strategy ma --fast 10 --slow 30 --capital 5000
```

### Comparar backtests

```bash
# Comparar dos backtests
python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json

# Comparar múltiples backtests con pesos personalizados
python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json ./reports/backtests/sol_1h_ma/metrics.json --w-sharpe 1.5 --w-drawdown 2.0 --w-profit-factor 1.0

# Con filtros de calidad y exportación de ranking
python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json ./reports/backtests/sol_1h_ma/metrics.json --min-trades 50 --min-sharpe 1.0 --export-json ./reports/ranking/top.json --export-csv ./reports/ranking/top.csv
```

### Paper Trading

```bash
# Iniciar simulación de paper trading
python -m scripts.run_paper_trading --symbol BTCUSDT --interval 1h --strategy ma --fast 20 --slow 50

# Ejecutar prospecting y scoring
python -m scripts.run_prospecting --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1d
```

### Sistema de Alertas y Reportes

```bash
# Generar reporte diario (JSON y Markdown)
python -m scripts.daily_report

# Generar reporte diario solo en formato JSON
python -m scripts.daily_report --format json

# Generar reporte diario solo en formato Markdown
python -m scripts.daily_report --format markdown

# Iniciar monitor de alertas (drawdown, precio, señales)
python -m scripts.alert_monitor --symbol BTCUSDT --interval 30s

# Ver el registro de decisiones (también disponible en el dashboard)
python -m scripts.view_decisions --limit 20

# Generar ranking de activos
python -m scripts.generate_ranking --symbols BTCUSDT,ETHUSDT,SOLUSDT --interval 1h
```

### Dashboard

```bash
# Iniciar el dashboard Streamlit
streamlit run app/dashboard/main.py
# O alternativamente:
python -m streamlit run app/dashboard/main.py
```

El dashboard proporciona acceso a:
- Overview: Métricas rápidas del portfolio y estado del sistema
- Market Analysis: Análisis detallado de activos individuales
- Asset Detail: Vista completa con scoring, recomendaciones y análisis multi-timeframe
- Prospects: Gestión de watchlist y ejecución de screeners
- Backtesting: Configuración y ejecución de backtests
- Portfolio: Visualización de posiciones y métricas de performance
- Journal: Análisis de comportamiento de trading
- Risk: Configuración y monitoreo de límites de riesgo
- Alerts: Gestión de reglas y notificaciones
- Logs: Visor de eventos del sistema

## Notas de seguridad

- Nunca usar API keys con permisos de retiro
- Para fases iniciales (analysis, backtest, paper) no se necesitan permisos de escritura en Binance
- Mantener `APP_MODE=analysis` y `KILL_SWITCH=true` como valores por defecto seguros
- Las API keys deben almacenarse en variables de entorno o `.env` (no commitear)
- El sistema incluye kill switch, circuit breakers y validaciones pre-orden

## Sistema de Calidad

Antes de cualquier commit, ejecutar el gate de calidad obligatorio:

```bash
python -m quality.quality_agent --check-all
```

Este sistema verifica:
- Gates de fase (pipeline de datos, backtesting, riesgo, paper trading, dashboard, conectividad Binance)
- Validadores de código (complejidad, seguridad, cobertura de pruebas, docstrings)
- Estilo y formato (ruff con línea de 100 caracteres)
- Tipado estático (mypy)
- Pruebas automatizadas (pytest)

## Convenciones del Proyecto

- Todos los timestamps en UTC milisegundos
- Los backtests deben modelar comisiones (0.1%) y slippage (0.1%)
- Las estrategias requieren ≥50 trades, profit factor >1.2, Sharpe >1 para promoción
- El tamaño de posición se basa en porcentaje de riesgo, no en cantidades fijas
- No se utilizan futuros o apalancamiento en la versión inicial
- Nunca commitear `.env`, `config/secrets.env`, `*.db`, o `reports/agent_logs/`

## Desarrollo

El proyecto sigue un roadmap por fases:

**Fase 1 (Completa)**: Base de datos y análisis histórico
**Fase 2 (Completa)**: Backtesting básico
**Fase 3 (En progreso)**: Motor de riesgo y paper trading
**Fase 4-5 (Planificada)**: Dashboard completo, analisis de mercado, reportes

Consulte `docs/roadmap_analisis.md` para el plan detallado de desarrollo.

## Plan Web (Opcion B)

Para migrar a una web mas estable (manteniendo el core en Python y creando un frontend moderno):
ver `docs/plan_migracion_web_opcion_b.md`.
