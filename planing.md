# Planning — App privada de inversión cripto

## 1. Resumen de la idea

Construir una aplicación privada para analizar el mercado de criptomonedas, probar estrategias, simular operaciones y, solo después de validar resultados, ejecutar inversiones reales con dinero propio.

La app no debe funcionar como una “IA que adivina el mercado”, sino como un sistema disciplinado de inversión basado en:

- datos históricos y en tiempo real;
- reglas de entrada y salida;
- backtesting;
- paper trading;
- control de riesgo;
- métricas de rendimiento;
- ejecución segura y limitada en Binance.

## 2. Objetivo principal

Crear una herramienta personal que ayude a invertir con más disciplina, reduciendo decisiones emocionales y evitando operaciones impulsivas.

El objetivo inicial no es maximizar ganancias, sino:

1. proteger capital;
2. validar estrategias;
3. medir riesgo;
4. automatizar reglas;
5. ejecutar operaciones pequeñas y controladas solo cuando el sistema esté probado.

## 3. Principios del proyecto

### 3.1 Seguridad primero

La app debe priorizar la protección del capital sobre cualquier intento de obtener rentabilidad.

Regla base:

> Antes de que la app intente ganar dinero, debe demostrar que sabe evitar pérdidas grandes.

### 3.2 Simulación antes que dinero real

No se debe conectar ejecución real con Binance hasta que existan:

- backtests consistentes;
- paper trading exitoso;
- métricas de riesgo aceptables;
- control de errores;
- límites de exposición;
- kill switch funcional.

### 3.3 Reglas antes que intuición

La app no debe operar porque “parece buen momento”. Cada operación debe venir de una regla clara, medible y auditable.

Ejemplo:

```text
Comprar BTC si:
- tendencia diaria positiva;
- precio sobre EMA 200;
- RSI entre 40 y 65;
- volumen relativo mayor a 1.2;
- drawdown del sistema menor al límite permitido;
- exposición total en BTC menor al máximo definido.
```

### 3.4 IA como asistente, no como operador

La IA puede ayudar a:

- explicar señales;
- resumir noticias;
- analizar sentimiento;
- detectar inconsistencias;
- generar reportes;
- sugerir mejoras de estrategia.

Pero la IA no debe tener permiso directo para ejecutar operaciones sin pasar por reglas estrictas de riesgo.

## 4. Alcance inicial

### Incluido en el MVP

- Descarga de datos históricos desde Binance.
- Watchlist de criptomonedas.
- Backtesting de estrategias simples.
- Cálculo de métricas de rendimiento.
- Simulación de cartera virtual.
- Registro de operaciones.
- Dashboard básico.
- Sistema de alertas.
- Configuración de riesgo.
- Modo paper trading.

### Fuera del MVP inicial

- Trading real automático.
- Futuros.
- Apalancamiento.
- Social trading.
- Gamificación.
- Competencias entre usuarios.
- App pública/comercial.
- Machine learning avanzado.
- Predicción pura de precios.

## 5. Roadmap por fases

## Fase 1 — Base de datos y análisis histórico

### Objetivo

Construir la base técnica para descargar, guardar y consultar datos históricos de mercado.

### Funcionalidades

- Conexión a Binance REST API.
- Descarga de velas OHLCV.
- Soporte inicial para BTC, ETH, SOL y monedas seleccionadas.
- Temporalidades iniciales:
  - 1h;
  - 4h;
  - 1d.
- Almacenamiento local de datos.
- Validación de datos faltantes o inconsistentes.

### Entregables

- Script de descarga de datos.
- Base de datos local.
- Funciones para consultar histórico por símbolo y timeframe.
- Primer notebook o reporte exploratorio.

### Criterio de éxito

La app puede descargar y consultar datos históricos de al menos 3 criptomonedas sin errores importantes.

---

## Fase 2 — Backtesting básico

### Objetivo

Probar estrategias simples con datos históricos.

### Estrategias iniciales

1. Cruce de medias móviles.
2. RSI simple.
3. Trend following.
4. DCA dinámico.
5. Rebalanceo simple BTC/ETH/stablecoin.

### Métricas mínimas

- ROI.
- Ganancia/pérdida total.
- Número de trades.
- Win rate.
- Profit factor.
- Maximum drawdown.
- Sharpe ratio.
- Pérdida promedio.
- Ganancia promedio.

### Reglas importantes

El backtesting debe incluir:

- comisiones;
- slippage;
- tamaño de posición;
- stop-loss;
- take-profit;
- capital inicial configurable.

### Criterio de éxito

La app puede comparar varias estrategias y mostrar cuál tuvo mejor rendimiento ajustado al riesgo, no solo mayor ganancia.

---

## Fase 3 — Motor de riesgo

### Objetivo

Crear un sistema que limite pérdidas y controle exposición.

### Reglas de riesgo iniciales

```text
Máximo por operación: 1% a 3% del capital
Riesgo máximo por operación: 0.5% a 1% del capital
Máxima pérdida diaria: 2% a 5%
Máxima pérdida semanal: 5% a 10%
Máxima exposición por moneda: 20% a 40%
Máxima exposición total en altcoins: 30% a 50%
No operar si hay datos incompletos
No operar si la API falla
No operar si la volatilidad supera el límite definido
No usar apalancamiento
No usar futuros en la primera versión
```

### Funcionalidades

- Cálculo automático de tamaño de posición.
- Stop-loss obligatorio.
- Take-profit opcional.
- Límite de operaciones por día.
- Bloqueo tras pérdida máxima.
- Kill switch manual.
- Validación antes de cada orden.

### Criterio de éxito

Ninguna operación puede ejecutarse si viola las reglas de riesgo.

---

## Fase 4 — Paper trading en tiempo real

### Objetivo

Simular operaciones en vivo sin usar dinero real.

### Funcionalidades

- Precios en tiempo real.
- Simulación de compras y ventas.
- Cartera virtual.
- Registro de señales.
- Registro de órdenes.
- Comparación entre precio esperado y precio simulado.
- Reporte diario/semanal.

### Criterio de éxito

La app puede operar durante varias semanas en modo simulado y producir reportes confiables.

---

## Fase 5 — Dashboard privado

### Objetivo

Crear una interfaz clara para monitorear mercado, señales, cartera y riesgo.

### Pantallas sugeridas

1. Dashboard general.
2. Watchlist.
3. Detalle de activo.
4. Backtesting.
5. Paper trading.
6. Riesgo.
7. Historial de operaciones.
8. Configuración.
9. Logs del sistema.

### Indicadores visuales

- Capital total.
- PnL diario.
- PnL acumulado.
- Drawdown actual.
- Exposición por moneda.
- Señales activas.
- Riesgo del mercado.
- Estado del sistema:
  - OK;
  - alerta;
  - bloqueado;
  - error.

### Criterio de éxito

Se puede entender el estado de la cartera y del sistema en menos de 30 segundos.

---

## Fase 6 — Conexión segura con Binance

### Objetivo

Conectar la app con Binance inicialmente en modo solo lectura.

### Etapa 1: Solo lectura

- Consultar balances.
- Consultar órdenes.
- Consultar historial.
- Consultar precios.
- No ejecutar operaciones.

### Etapa 2: Trading manual asistido

- La app sugiere una operación.
- El usuario confirma manualmente.
- La app ejecuta solo si pasa controles de riesgo.

### Etapa 3: Automatización limitada

- Operaciones automáticas pequeñas.
- Límites estrictos.
- Monitoreo constante.
- Kill switch activo.
- Logs obligatorios.

### Reglas de seguridad para API keys

- Nunca habilitar retiros en la API key.
- Usar permisos mínimos necesarios.
- Usar variables de entorno o almacenamiento cifrado.
- Rotar claves periódicamente.
- Separar API key de lectura y API key de trading.
- Bloquear ejecución si la configuración es insegura.

### Criterio de éxito

La app puede conectarse a Binance sin exponer claves y sin permitir operaciones fuera de los límites definidos.

---

## Fase 7 — IA ligera y análisis avanzado

### Objetivo

Agregar inteligencia auxiliar sin convertir la app en una caja negra.

### Funciones posibles

- Resumen de mercado diario.
- Explicación de señales.
- Análisis de sentimiento.
- Detección de noticias relevantes.
- Generación de reporte semanal.
- Sugerencias para mejorar estrategias.
- Detección de comportamiento impulsivo.

### Restricción crítica

La IA no ejecuta operaciones directamente.

Cada recomendación debe ser explicable y pasar por el motor de riesgo.

## 6. Arquitectura propuesta

```text
/app
  /data
    binance_client.py
    market_data.py
    data_validator.py

  /database
    models.py
    connection.py
    migrations.py

  /strategies
    base_strategy.py
    moving_average.py
    rsi_strategy.py
    trend_following.py
    dca_dynamic.py
    rebalance.py

  /backtesting
    engine.py
    metrics.py
    walk_forward.py
    reports.py

  /risk
    position_sizing.py
    stop_loss.py
    exposure_limits.py
    circuit_breakers.py

  /paper_trading
    simulator.py
    virtual_portfolio.py
    virtual_orders.py

  /execution
    binance_executor.py
    order_manager.py
    safety_checks.py

  /alerts
    alert_engine.py
    notifications.py

  /dashboard
    main.py
    pages/
      dashboard.py
      watchlist.py
      backtesting.py
      portfolio.py
      risk.py
      logs.py

  /ai
    market_summary.py
    signal_explainer.py
    journal_analyzer.py

  /config
    settings.yaml
    secrets.example.env

  /tests
    test_backtesting.py
    test_risk.py
    test_strategies.py
    test_execution.py
```

## 7. Componentes principales

## 7.1 Módulo de datos

Responsable de obtener y limpiar datos.

### Requisitos

- Descargar datos históricos.
- Recibir precios en tiempo real.
- Validar datos faltantes.
- Evitar duplicados.
- Normalizar símbolos.
- Manejar errores de API.
- Respetar rate limits.

### Fuentes iniciales

- Binance REST API para histórico.
- Binance WebSocket para tiempo real.
- Opcional futuro:
  - CoinGecko;
  - CryptoPanic;
  - LunarCrush;
  - Glassnode;
  - DefiLlama.

## 7.2 Módulo de estrategias

Responsable de generar señales.

### Señales posibles

```text
BUY
SELL
HOLD
REDUCE
EXIT
```

### Cada señal debe incluir

- símbolo;
- timeframe;
- timestamp;
- precio;
- razón de entrada;
- confianza;
- riesgo;
- stop-loss sugerido;
- take-profit sugerido;
- tamaño de posición sugerido.

## 7.3 Módulo de backtesting

Responsable de probar estrategias con datos históricos.

### Debe evitar

- look-ahead bias;
- sobreajuste;
- ignorar comisiones;
- ignorar slippage;
- usar datos futuros;
- medir solo ROI.

### Requisitos avanzados futuros

- Walk-forward validation.
- Comparación in-sample vs out-of-sample.
- Pruebas en diferentes ciclos de mercado.
- Stress testing.
- Market replay.

## 7.4 Módulo de riesgo

Responsable de aprobar o rechazar operaciones.

### Este módulo tiene autoridad final

Aunque una estrategia genere señal de compra, el motor de riesgo puede bloquearla.

Ejemplo:

```text
Señal: BUY BTC
Resultado riesgo: REJECTED
Motivo: exposición máxima en BTC ya alcanzada.
```

## 7.5 Módulo de ejecución

Responsable de enviar órdenes reales a Binance.

### Regla

Este módulo solo se activa después de pasar por:

1. estrategia;
2. motor de riesgo;
3. safety checks;
4. configuración de modo real;
5. confirmación manual o automatización autorizada.

## 8. Modos de operación

## 8.1 Modo análisis

La app solo analiza mercado y genera señales.

```text
MODE=analysis
```

No hay operaciones simuladas ni reales.

## 8.2 Modo backtest

La app prueba estrategias con datos históricos.

```text
MODE=backtest
```

## 8.3 Modo paper trading

La app simula operaciones en vivo.

```text
MODE=paper
```

## 8.4 Modo real manual

La app sugiere operaciones y el usuario confirma.

```text
MODE=real_manual
```

## 8.5 Modo real automático limitado

La app puede ejecutar operaciones reales pequeñas bajo reglas estrictas.

```text
MODE=real_auto_limited
```

Este modo debe estar bloqueado por defecto.

## 9. Estrategias iniciales

## 9.1 Cruce de medias móviles

### Idea

Comprar cuando una media móvil rápida cruza por encima de una lenta. Vender cuando cruza hacia abajo.

### Parámetros

- EMA rápida: 20.
- EMA lenta: 50.
- Timeframe: 4h o 1d.

### Riesgos

- Puede fallar en mercados laterales.
- Puede entrar tarde después de un movimiento fuerte.

## 9.2 RSI simple

### Idea

Detectar sobrecompra y sobreventa.

### Parámetros

- RSI período: 14.
- Compra potencial: RSI < 30.
- Venta potencial: RSI > 70.

### Riesgos

- En tendencias fuertes, RSI puede mantenerse sobrecomprado o sobrevendido mucho tiempo.

## 9.3 Trend following

### Idea

Operar solo en dirección de la tendencia principal.

### Reglas ejemplo

```text
Comprar si:
- precio > EMA 200 diaria;
- EMA 20 > EMA 50;
- volumen relativo > 1;
- RSI entre 40 y 70.
```

## 9.4 DCA dinámico

### Idea

Comprar gradualmente, aumentando o reduciendo compras según condiciones de mercado.

### Ejemplo

```text
Compra base semanal: 100 USDT
Si BTC cae 10% desde máximo reciente: comprar 150 USDT
Si BTC cae 20%: comprar 200 USDT
Si precio está debajo de EMA 200 y tendencia débil: reducir compra a 50 USDT
```

## 9.5 Rebalanceo

### Idea

Mantener porcentajes objetivo.

Ejemplo:

```text
BTC: 50%
ETH: 30%
Stablecoins: 20%
```

Rebalancear si una posición se desvía más de cierto umbral.

## 10. Métricas de rendimiento

Cada estrategia debe mostrar:

| Métrica | Descripción |
|---|---|
| ROI | Retorno total |
| CAGR | Retorno anual compuesto |
| Maximum Drawdown | Peor caída desde máximo a mínimo |
| Sharpe Ratio | Rentabilidad ajustada al riesgo |
| Sortino Ratio | Rentabilidad ajustada a volatilidad negativa |
| Win Rate | Porcentaje de operaciones ganadoras |
| Profit Factor | Ganancia bruta / pérdida bruta |
| Expectancy | Ganancia esperada por operación |
| Trades Totales | Número de operaciones |
| Avg Win | Ganancia promedio |
| Avg Loss | Pérdida promedio |
| Payoff Ratio | Avg Win / Avg Loss |
| Tiempo en mercado | Porcentaje del tiempo con posición abierta |

## 11. Reglas de aprobación de estrategia

Una estrategia no debería pasar a paper trading si:

- tiene drawdown demasiado alto;
- depende de muy pocos trades;
- solo funciona en una moneda;
- solo funciona en un período específico;
- ignora comisiones;
- se rompe con slippage;
- su rendimiento viene de una sola operación grande;
- tiene mal desempeño en out-of-sample;
- es demasiado compleja para explicar.

### Criterios mínimos sugeridos

```text
Trades mínimos: 50
Drawdown máximo: configurable, idealmente < 20%
Profit factor: > 1.2
Sharpe ratio: > 1
Win rate: no obligatorio alto si payoff es bueno
Resultado positivo después de comisiones y slippage
```

## 12. Seguridad

## 12.1 Principios

- No guardar claves en texto plano.
- No habilitar retiros.
- No exponer secretos en logs.
- No subir claves a GitHub.
- Usar `.env` para secretos locales.
- Usar `.gitignore`.
- Validar toda orden antes de enviarla.
- Registrar toda operación.
- Tener kill switch.

## 12.2 Kill switch

Variable global de seguridad:

```text
KILL_SWITCH=true
```

Si está activo:

- no se abren operaciones nuevas;
- se pueden cerrar posiciones si está permitido;
- se pausa automatización;
- se genera alerta.

## 12.3 Circuit breakers

La app debe bloquear trading si:

- pérdida diaria supera el límite;
- error repetido de API;
- precio no actualizado;
- spread demasiado alto;
- volatilidad extrema;
- balance inconsistente;
- diferencia fuerte entre precio esperado y precio real;
- falla el cálculo de riesgo.

## 13. Configuración inicial sugerida

```yaml
capital:
  initial_usdt: 1000

risk:
  max_position_size_pct: 0.03
  max_risk_per_trade_pct: 0.01
  max_daily_loss_pct: 0.03
  max_weekly_loss_pct: 0.07
  max_asset_exposure_pct: 0.35
  max_altcoin_exposure_pct: 0.40

trading:
  mode: paper
  allow_real_trading: false
  allow_futures: false
  allow_leverage: false
  require_stop_loss: true
  require_take_profit: false

fees:
  trading_fee_pct: 0.001
  slippage_pct: 0.001

symbols:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT

timeframes:
  - 1h
  - 4h
  - 1d
```

## 14. Modelo de datos inicial

## 14.1 MarketCandle

```text
symbol
timeframe
timestamp
open
high
low
close
volume
source
```

## 14.2 Signal

```text
id
timestamp
symbol
timeframe
strategy
action
price
confidence
risk_score
reason
stop_loss
take_profit
position_size
status
```

## 14.3 Trade

```text
id
mode
timestamp_open
timestamp_close
symbol
side
entry_price
exit_price
quantity
fees
pnl
pnl_pct
strategy
reason_entry
reason_exit
status
```

## 14.4 Portfolio

```text
id
mode
timestamp
cash_balance
asset_balances
total_value
exposure
drawdown
```

## 15. Requerimientos funcionales

## Datos

- La app debe descargar datos históricos.
- La app debe actualizar precios.
- La app debe detectar datos faltantes.
- La app debe guardar datos localmente.

## Backtesting

- La app debe ejecutar estrategias sobre datos históricos.
- La app debe calcular métricas.
- La app debe comparar estrategias.
- La app debe incluir comisiones y slippage.
- La app debe exportar resultados.

## Simulación

- La app debe crear cartera virtual.
- La app debe simular compras y ventas.
- La app debe registrar operaciones.
- La app debe mostrar PnL.

## Riesgo

- La app debe calcular tamaño de posición.
- La app debe exigir stop-loss.
- La app debe bloquear operaciones peligrosas.
- La app debe tener kill switch.

## Binance

- La app debe iniciar con conexión solo lectura.
- La app no debe permitir retiros.
- La app debe validar permisos de API.
- La app debe registrar toda orden enviada.

## Dashboard

- La app debe mostrar cartera.
- La app debe mostrar señales.
- La app debe mostrar riesgo.
- La app debe mostrar histórico.
- La app debe mostrar estado del sistema.

## 16. Requerimientos no funcionales

## Seguridad

- Cifrado de secretos.
- Protección de API keys.
- Logs sin datos sensibles.
- Validaciones antes de operar.

## Confiabilidad

- Manejo de errores.
- Reintentos controlados.
- Validación de datos.
- Tests automáticos.

## Rendimiento

- Backtest de 1 año en tiempo razonable.
- Dashboard fluido.
- Actualizaciones de precio eficientes.

## Mantenibilidad

- Código modular.
- Estrategias separadas.
- Tests por módulo.
- Configuración centralizada.

## Auditoría

- Cada señal debe guardar razón.
- Cada orden debe guardar estado.
- Cada error debe quedar registrado.
- Cada cambio de configuración importante debe registrarse.

## 17. Stack técnico sugerido

## Opción simple para empezar

```text
Python
Pandas
NumPy
SQLite
FastAPI
Streamlit
python-binance o binance-connector
Plotly
```

### Ventajas

- Rápido para prototipar.
- Bueno para análisis de datos.
- Fácil de usar en local.
- Ideal para backtesting inicial.

## Opción más escalable

```text
Backend: Python + FastAPI
Frontend: React / Next.js
Base de datos: PostgreSQL
Cache: Redis
Workers: Celery / RQ
Charts: TradingView Lightweight Charts
Deploy: VPS privado o servidor local
```

### Recomendación

Empezar simple con Python + SQLite + Streamlit.  
Migrar a arquitectura más compleja solo cuando el sistema esté validado.

## 18. Plan de desarrollo inicial de 4 semanas

## Semana 1

- Crear repositorio.
- Definir estructura del proyecto.
- Conectar Binance REST.
- Descargar datos históricos.
- Guardar en SQLite.
- Crear primeras gráficas.

## Semana 2

- Implementar 2 estrategias:
  - medias móviles;
  - RSI.
- Crear motor de backtesting.
- Calcular ROI, drawdown y win rate.
- Añadir comisiones y slippage.

## Semana 3

- Crear motor de riesgo.
- Añadir tamaño de posición.
- Añadir stop-loss.
- Añadir take-profit.
- Crear cartera virtual.

## Semana 4

- Crear dashboard básico.
- Mostrar señales.
- Mostrar operaciones.
- Mostrar métricas.
- Exportar reporte.
- Definir si pasa a paper trading.

## 19. Checklist antes de operar dinero real

No activar trading real hasta cumplir todo esto:

```text
[ ] Backtesting funcionando.
[ ] Paper trading funcionando.
[ ] Mínimo varias semanas de simulación.
[ ] Comisiones incluidas.
[ ] Slippage incluido.
[ ] Stop-loss obligatorio.
[ ] Kill switch probado.
[ ] Límite diario de pérdida probado.
[ ] API key sin permiso de retiro.
[ ] Logs funcionando.
[ ] Errores de API manejados.
[ ] Estrategia documentada.
[ ] Tamaño de posición limitado.
[ ] Modo real desactivado por defecto.
[ ] Confirmación manual disponible.
```

## 20. Riesgos principales

## Riesgo de mercado

El mercado cripto puede caer rápidamente y con alta volatilidad.

## Riesgo técnico

La app puede fallar por bugs, datos incorrectos o errores de API.

## Riesgo de sobreajuste

Una estrategia puede verse rentable en el pasado y fallar en vivo.

## Riesgo de ejecución

El precio real puede ser peor que el precio esperado.

## Riesgo de seguridad

Una API key mal protegida puede comprometer fondos.

## Riesgo emocional

El usuario puede desactivar reglas, mover stops o aumentar riesgo después de pérdidas.

## 21. Reglas personales recomendadas

```text
No operar con dinero que no puedo perder.
No usar apalancamiento al inicio.
No aumentar tamaño de operación después de una pérdida.
No modificar una estrategia durante una operación abierta.
No apagar el stop-loss.
No operar si el sistema está en error.
No operar por FOMO.
No operar monedas sin liquidez suficiente.
No concentrar todo en una sola moneda.
No activar trading automático sin paper trading previo.
```

## 22. Definición de éxito del MVP

El MVP será exitoso si permite:

1. descargar datos históricos;
2. probar estrategias simples;
3. medir riesgo;
4. simular operaciones;
5. mostrar resultados claramente;
6. bloquear operaciones peligrosas;
7. preparar una futura conexión segura con Binance.

## 23. Próximos pasos inmediatos

1. Crear repositorio del proyecto.
2. Elegir stack inicial.
3. Definir monedas iniciales.
4. Implementar descarga de datos.
5. Crear primer backtest simple.
6. Crear configuración de riesgo.
7. Crear dashboard básico.
8. Ejecutar pruebas con datos históricos.
9. Pasar a paper trading.
10. Evaluar si vale la pena conectar Binance real.

## 24. Nombre provisional

Opciones:

- CryptoPilot
- QuantCripto
- RiskFirst Crypto
- AlphaGuard
- CriptoLab
- Private Crypto Trader
- BotRisk

Nombre recomendado por ahora:

```text
CriptoLab
```

Porque comunica que la app es primero un laboratorio de pruebas, no una promesa de ganancias.

## 25. Nota final

Este proyecto debe construirse con mentalidad defensiva.

La pregunta principal no debe ser:

> ¿Cuánto puedo ganar?

La pregunta principal debe ser:

> ¿Cuánto puedo perder y cómo lo limito?

Si la app logra responder eso de manera clara y automática, tendrá una base sólida para convertirse en una herramienta real de inversión personal.
