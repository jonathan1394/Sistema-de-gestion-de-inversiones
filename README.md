# CriptoLab

Base inicial del sistema privado de inversion cripto, enfocada en Fase 1:

- descarga de velas historicas desde Binance REST;
- almacenamiento en SQLite;
- validacion simple de continuidad de velas;
- configuracion segura por `settings.yaml` + variables de entorno.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Descargar historico

Ejemplo para BTCUSDT en velas de 1 hora:

```bash
python -m scripts.download_historical --symbol BTCUSDT --interval 1h --limit 1000
```

Con rango temporal (milisegundos UTC):

```bash
python -m scripts.download_historical --symbol ETHUSDT --interval 4h --start-ms 1704067200000 --end-ms 1711929600000
```

Con descarga paginada para rangos largos:

```bash
python -m scripts.download_historical --symbol BTCUSDT --interval 1h --start-ms 1672531200000 --end-ms 1704067200000 --paginate --max-batches 200
```

## Consultar datos guardados

Puedes reutilizar `get_candles` desde `app/data/market_data.py` para leer velas desde SQLite:

```python
from app.config import load_settings
from app.database.connection import get_connection
from app.data.market_data import get_candles

config = load_settings("settings.yaml")
conn = get_connection(config.database.path)

candles = get_candles(
    connection=conn,
    symbol="BTCUSDT",
    interval="1h",
    start_time_ms=1704067200000,
    end_time_ms=1706745600000,
)
print(len(candles), candles[0].close)
```

## Notas de seguridad

- no uses claves con permisos de retiro;
- para Fase 1 no se necesita trading ni permisos de escritura en Binance;
- manten `APP_MODE=analysis` y `KILL_SWITCH=true` por defecto.

## Backtest minimo (MA crossover)

Ejecuta un backtest sobre datos ya guardados en SQLite:

```bash
python -m scripts.run_backtest_ma --symbol BTCUSDT --interval 1h --start-ms 1704067200000 --end-ms 1711929600000 --fast 20 --slow 50 --capital 1000
```

Con export de resultados:

```bash
python -m scripts.run_backtest_ma --symbol BTCUSDT --interval 1h --start-ms 1704067200000 --end-ms 1711929600000 --export-dir ./reports/backtests/btc_1h_ma
```

Ese comando genera:

- `metrics.json`
- `trades.csv`
- `equity_curve.csv`

Parametros clave:

- `--commission` y `--slippage` usan formato decimal (0.001 = 0.1%).
- `--fast` debe ser menor que `--slow` para una configuracion clasica.

## Comparar backtests

Si ya tienes corridas con `metrics.json`, puedes compararlas rapido:

```bash
python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json
```

Tambien puedes pasar mas de dos archivos y definir pesos por metrica:

```bash
python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json ./reports/backtests/sol_1h_ma/metrics.json --w-sharpe 1.5 --w-drawdown 2.0 --w-profit-factor 1.0
```

Con filtros minimos y export del ranking:

```bash
python -m scripts.compare_backtests --files ./reports/backtests/btc_1h_ma/metrics.json ./reports/backtests/eth_4h_ma/metrics.json ./reports/backtests/sol_1h_ma/metrics.json --min-trades 50 --min-sharpe 1.0 --export-json ./reports/ranking/top.json --export-csv ./reports/ranking/top.csv
```

El comparador muestra:

- tabla con Sharpe, drawdown, profit factor, ROI, win rate y total de trades;
- ranking ponderado por Sharpe, drawdown absoluto menor y profit factor;
- filtros por `min_trades` y `min_sharpe` para excluir corridas debiles;
- export opcional de ranking a JSON y CSV;
- compatibilidad legacy con `--a` y `--b` para comparacion de dos archivos.
