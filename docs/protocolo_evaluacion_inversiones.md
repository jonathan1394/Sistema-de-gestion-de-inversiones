# Protocolo Oficial de Evaluacion de Inversiones

## Objetivo

Convertir el sistema en un proceso repetible para evaluar oportunidades, no solo para visualizar datos.

## Universo oficial

- Simbolos: los definidos en `settings.yaml` bajo `symbols`
- Timeframes oficiales: los definidos en `settings.yaml` bajo `timeframes`
- Intervalo primario de prospecting: `1d` salvo que se indique otro en la revision
- Intervalo sugerido de backtest comparativo: `4h`

## Secuencia obligatoria

1. Validar calidad operativa del codigo con `python -m quality.quality_agent --check-all`
2. Confirmar frescura y continuidad de datos para los simbolos/timeframes del universo
3. Ejecutar o revisar prospecting y ranking
4. Revisar confluencia multi-timeframe y recomendacion
5. Ejecutar comparativa de backtest sobre el activo
6. Pasar la oportunidad por evaluacion de riesgo
7. Registrar la conclusion como una de estas salidas:
   - `investable`
   - `review_required`
   - `blocked`

## Reglas minimas de promocion

- Score >= `prospecting.recommendation.invertir_threshold`
- Confluencia >= `prospecting.recommendation.min_confluence_for_invertir`
- Backtest con al menos `backtesting.min_trades_for_validation` trades
- Profit factor > `backtesting.min_profit_factor`
- Sharpe > `backtesting.min_sharpe_ratio`
- Evaluacion de riesgo aprobada
- Datos frescos, continuos y con historial suficiente

## Flujo soportado por la aplicacion

- API consolidada: `GET /api/v1/evaluation/investment/{symbol}`
- Salud de datos: `GET /api/v1/evaluation/data-health`
- Frontend consolidado: `/investment-review`
- Rutina CLI: `python -m scripts.run_investment_review`

## Rutina diaria recomendada

1. `python -m quality.quality_agent --check-all`
2. Actualizar dataset necesario del universo
3. `python -m scripts.run_prospecting scan-all`
4. `python -m scripts.run_investment_review`
5. Abrir `/investment-review?symbol=BTCUSDT` y repetir por activo prioritario

## Interpretacion de estados

- `investable`: pasa datos, score/confluencia, backtest y riesgo
- `review_required`: hay senal interesante pero falta validar una o mas capas
- `blocked`: el activo falla una condicion operativa clave
