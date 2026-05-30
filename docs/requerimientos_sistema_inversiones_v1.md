# Documento de Requerimientos - CriptoLab

**Proyecto:** Sistema de gestion de inversiones / CriptoLab  
**Version:** 1.0  
**Fecha:** 2026-05-30  
**Estado:** Propuesto para revision tecnica  
**Repositorio:** `jonathan1394/Sistema-de-gestion-de-inversiones`  
**Audiencia:** tecnicos, desarrolladores, analistas cuantitativos, responsables de riesgo y operadores del sistema.

---

## 1. Proposito del documento

Este documento define los requerimientos funcionales, no funcionales, tecnicos y de gobierno para evolucionar CriptoLab hacia una plataforma privada de gestion de inversiones cripto con enfoque profesional, disciplinado, trazable y seguro.

El objetivo no es construir un bot que opere automaticamente sin control, sino una plataforma de decision de inversion que permita:

1. Analizar activos cripto con datos historicos y actuales.
2. Validar estrategias mediante backtesting robusto.
3. Simular ejecucion mediante paper trading persistente.
4. Controlar riesgo antes de cualquier decision operativa.
5. Registrar cada senal, decision, rechazo, aprobacion y ejecucion.
6. Promover estrategias gradualmente segun evidencia cuantitativa.
7. Mantener trading real deshabilitado por defecto.
8. Usar IA solo como apoyo analitico, no como autoridad final de ejecucion.

---

## 2. Vision del sistema

CriptoLab debe funcionar como una mesa privada de inversion:

- **Laboratorio cuantitativo:** prueba estrategias, parametros, activos y timeframes.
- **Motor de riesgo:** valida exposicion, drawdown, stop-loss, tamano de posicion y condiciones de mercado.
- **Sistema de gobierno:** controla que activos, estrategias y modos estan permitidos.
- **Dashboard operativo:** muestra portfolio, senales, riesgo, alertas, logs y resultados.
- **Asistente analitico:** explica senales, resume mercado y ayuda a detectar sesgos, sin ejecutar operaciones.
- **Sistema de auditoria:** conserva evidencias de cada decision y cambio relevante.

---

## 3. Principios rectores aprobados

### 3.1 Preservacion de capital

El sistema debe priorizar la preservacion del capital por encima de la maximizacion de retorno. Toda estrategia debe demostrar control de perdidas, limites de drawdown y comportamiento aceptable en escenarios adversos.

### 3.2 Senal no implica orden

Ninguna senal tecnica, estadistica o generada por IA puede convertirse directamente en orden. Toda senal debe pasar por:

```text
Signal -> Market Context -> Investment Policy -> Risk Manager -> Safety Checks -> Approval -> Execution/Paper Execution
```

### 3.3 Trading real bloqueado por defecto

Los modos `real_manual` y `real_auto_limited` deben permanecer bloqueados por defecto hasta que existan controles de seguridad, auditoria, aprobacion humana y limites operativos suficientes.

### 3.4 Spot only en la version inicial

La version inicial debe prohibir:

- Futuros.
- Leverage.
- Margin trading.
- Short selling.
- Activos iliquidos.
- Tokens sin historial suficiente.
- Activos fuera de whitelist.

### 3.5 IA como analista, no como trader autonomo

La IA puede resumir, explicar, clasificar, detectar patrones y proponer hipotesis, pero no puede:

- Ejecutar operaciones.
- Modificar limites de riesgo.
- Activar trading real.
- Saltarse politica de inversion.
- Cambiar capital asignado.
- Aprobar estrategias para produccion.

### 3.6 Trazabilidad completa

Cada senal, decision, rechazo, aprobacion, ejecucion, cambio de configuracion y promocion de estrategia debe quedar registrada.

---

## 4. Alcance funcional

### 4.1 Incluido en esta evolucion

- Politica formal de inversion.
- Whitelist y blacklist de activos.
- Gestion de capital por bolsillos.
- Motor de promocion de estrategias.
- Backtesting robusto.
- Walk-forward testing.
- Analisis out-of-sample.
- Monte Carlo sobre secuencia de trades.
- Deteccion de regimen de mercado.
- Matriz de correlacion.
- Gestion de portfolio.
- Decision log y audit trail.
- Aprobaciones humanas para modo real manual.
- Alertas de riesgo y operacion.
- Dashboard ejecutivo y operativo.
- Gobernanza de IA.
- Seguridad de secretos y API keys.
- Quality gates obligatorios.

### 4.2 Fuera de alcance inicial

- Custodia propia de criptoactivos.
- Gestion de wallets on-chain.
- DeFi.
- NFT.
- Yield farming.
- Futuros.
- Apalancamiento.
- Market making.
- Arbitraje de alta frecuencia.
- Trading completamente autonomo sin supervision.
- Recomendaciones financieras para terceros.

---

## 5. Estados operativos del sistema

El sistema debe soportar los siguientes modos:

| Modo | Descripcion | Permitir orden real | Requiere aprobacion humana | Estado inicial |
|---|---|---:|---:|---|
| `analysis` | Solo analisis y descarga de datos | No | No | Habilitado |
| `backtest` | Ejecucion de backtests | No | No | Habilitado |
| `paper` | Simulacion persistente | No | No | Habilitado |
| `real_manual` | Operacion real con confirmacion humana | Si | Si | Bloqueado |
| `real_auto_limited` | Operacion real automatica limitada | Si | Configurable | Bloqueado |

### Reglas obligatorias

- `KILL_SWITCH=true` debe bloquear cualquier ejecucion paper o real que implique apertura de nuevas posiciones.
- `allow_real_trading=false` debe impedir el uso de cualquier executor real.
- Si una API key tiene permiso de retiro, el sistema debe rechazar su uso.
- Si el modo es invalido, el sistema debe fallar cerrado.

---

## 6. Requerimientos funcionales

## 6.1 Modulo de Politica de Inversion

### Objetivo

Definir formalmente que puede hacer el sistema, bajo que condiciones y con que limites.

### Ubicacion propuesta

```text
app/policy/
  investment_policy.py
  asset_universe.py
  capital_allocation.py
  prohibited_assets.py
  strategy_promotion.py
  policy_loader.py
```

### RF-POL-001 - Politica global de inversion

El sistema debe permitir definir una politica global en `settings.yaml` o archivo dedicado `policy.yaml`.

Debe incluir como minimo:

- Capital total autorizado.
- Porcentaje minimo de cash/reserva.
- Exposicion maxima total.
- Exposicion maxima por activo.
- Exposicion maxima por altcoins.
- Exposicion maxima por estrategia.
- Activos permitidos.
- Activos prohibidos.
- Timeframes permitidos.
- Modos operativos permitidos.
- Reglas de promocion de estrategias.

### RF-POL-002 - Whitelist de activos

El sistema debe operar solo activos presentes en whitelist cuando se trate de paper trading avanzado, real manual o real automatico limitado.

Campos minimos:

```yaml
asset_universe:
  whitelist:
    - symbol: BTCUSDT
      category: core
      min_history_days: 730
      max_position_pct: 0.35
      enabled: true
    - symbol: ETHUSDT
      category: core
      min_history_days: 730
      max_position_pct: 0.25
      enabled: true
```

### RF-POL-003 - Blacklist de activos

El sistema debe rechazar activos prohibidos por categoria o simbolo.

Categorias iniciales prohibidas:

- Meme coins.
- Tokens sin volumen suficiente.
- Tokens con menos de N dias de historial.
- Tokens con spreads altos.
- Tokens recientemente listados.
- Tokens detectados como extremadamente volatiles.

### RF-POL-004 - Bolsillos de capital

El sistema debe separar capital en bolsillos logicos:

| Bolsillo | Descripcion | Uso |
|---|---|---|
| `reserve` | Reserva no operativa | No se invierte |
| `core` | BTC/ETH u otros activos principales | Inversion base |
| `systematic` | Estrategias validadas | Trading sistematico |
| `experimental` | Estrategias nuevas | Riesgo controlado |
| `cash` | Liquidez operativa | Espera y proteccion |

### RF-POL-005 - Evaluador de politica

Debe existir una funcion central:

```python
def evaluate_policy(signal, strategy, asset, portfolio, market_context) -> PolicyDecision:
    ...
```

La respuesta debe incluir:

- `approved: bool`
- `reason: str`
- `blocking_rule: str | None`
- `warnings: list[str]`
- `policy_snapshot: dict`

### Criterios de aceptacion

- Una senal sobre un activo no autorizado es rechazada.
- Una estrategia no promovida es rechazada.
- Una senal que supera exposicion por activo es rechazada.
- Las decisiones de politica quedan registradas en decision log.
- Las reglas pueden modificarse sin cambiar codigo.

---

## 6.2 Modulo de Promocion de Estrategias

### Objetivo

Evitar que una estrategia pase a paper trading o trading real sin evidencia suficiente.

### Estados de estrategia

| Estado | Descripcion |
|---|---|
| `draft` | Idea inicial |
| `research` | En analisis historico |
| `backtest_candidate` | Lista para backtesting amplio |
| `paper_candidate` | Apta para simulacion persistente |
| `paper_active` | Corriendo en paper trading |
| `real_manual_candidate` | Candidata a real con confirmacion humana |
| `real_manual_active` | Activa en real manual |
| `real_auto_candidate` | Candidata a automatizacion limitada |
| `real_auto_limited` | Automatizada con limites estrictos |
| `rejected` | Descartada |
| `paused` | Pausada por riesgo o bajo desempeno |

### RF-STR-001 - Ficha de estrategia

Cada estrategia debe tener una ficha persistente con:

- Nombre.
- Version.
- Hipotesis.
- Autor.
- Fecha de creacion.
- Activos permitidos.
- Timeframes permitidos.
- Parametros.
- Estado.
- Evidencias de backtesting.
- Evidencias de paper trading.
- Riesgos conocidos.
- Fecha de ultima revision.

### RF-STR-002 - Reglas minimas de promocion

Una estrategia no puede promoverse a paper trading si no cumple:

- Minimo 50 trades en backtest.
- Profit factor > 1.2.
- Sharpe ratio > 1.0.
- Max drawdown dentro del limite definido.
- Backtest con comision y slippage.
- Prueba out-of-sample aprobada.
- Sin dependencia excesiva de un unico parametro.

### RF-STR-003 - Promocion a real manual

Una estrategia solo puede pasar a `real_manual_candidate` si cumple:

- Paper trading minimo 30 dias o N operaciones.
- No rompe limites diarios/semanales.
- Drawdown realista dentro de tolerancia.
- Diferencia aceptable entre backtest y paper trading.
- Aprobacion manual registrada.

### RF-STR-004 - Promocion a real automatico limitado

Una estrategia solo puede pasar a `real_auto_limited` si cumple:

- Historial prolongado en paper y real manual.
- Cero incidentes criticos.
- Kill switch probado.
- Alertas activas.
- Limites por orden, dia, semana y estrategia.
- Aprobacion explicita.

### Criterios de aceptacion

- No se puede ejecutar una estrategia en modo superior a su estado aprobado.
- Toda promocion genera un registro de auditoria.
- Toda degradacion o pausa queda registrada con motivo.
- El dashboard muestra el estado de cada estrategia.

---

## 6.3 Backtesting Robusto

### Objetivo

Validar estrategias reduciendo riesgo de sobreajuste.

### RF-BT-001 - Backtest con costos realistas

Todo backtest debe contemplar:

- Comisiones.
- Slippage.
- Spread estimado.
- Latencia simulada cuando corresponda.
- Tamanos de posicion segun riesgo.
- Stop-loss si la politica lo exige.

### RF-BT-002 - Walk-forward testing

El sistema debe permitir dividir datos historicos en ventanas:

```text
Train 1 -> Test 1
Train 2 -> Test 2
Train 3 -> Test 3
...
```

Debe calcular metricas por ventana y metricas consolidadas.

### RF-BT-003 - Out-of-sample testing

El sistema debe separar un periodo no utilizado para optimizacion y validar la estrategia sobre ese periodo.

### RF-BT-004 - Monte Carlo de trades

El sistema debe tomar la lista historica de trades y simular multiples permutaciones para estimar:

- Riesgo de ruina.
- Drawdown probable.
- Peor racha esperada.
- Distribucion de retornos.
- Capital minimo recomendado.

### RF-BT-005 - Sensibilidad de parametros

El sistema debe evaluar si una estrategia depende de parametros demasiado especificos.

Ejemplo:

```text
MA fast: 10, 15, 20, 25
MA slow: 40, 50, 60, 80
```

Debe advertir si solo una combinacion aislada funciona.

### RF-BT-006 - Clasificacion por regimen de mercado

Los resultados deben segmentarse por regimen:

- Alcista.
- Bajista.
- Lateral.
- Alta volatilidad.
- Baja volatilidad.
- Risk-on.
- Risk-off.

### Metricas obligatorias

| Metrica | Obligatoria |
|---|---:|
| Total return | Si |
| CAGR o retorno anualizado | Si |
| Max drawdown | Si |
| Profit factor | Si |
| Sharpe ratio | Si |
| Sortino ratio | Si |
| Calmar ratio | Si |
| Win rate | Si |
| Avg win / Avg loss | Si |
| Expectancy | Si |
| Exposure time | Si |
| Consecutive losses | Si |
| Number of trades | Si |
| Fees total | Si |
| Slippage total estimado | Si |

### Criterios de aceptacion

- Un backtest sin costos no puede ser usado para promocion.
- Una estrategia con pocos trades no puede ser promovida.
- Los reportes deben exportarse a JSON y CSV.
- El dashboard debe poder comparar estrategias.

---

## 6.4 Motor de Riesgo

### Objetivo

Centralizar todos los controles de riesgo antes de aprobar una operacion.

### RF-RISK-001 - Evaluacion multicapa

El motor de riesgo debe evaluar en orden:

1. Kill switch.
2. Modo operativo.
3. Politica de inversion.
4. Circuit breakers.
5. Regimen de mercado.
6. Stop-loss.
7. Tamano de posicion.
8. Exposicion por activo.
9. Exposicion por categoria.
10. Exposicion total.
11. Correlacion de portfolio.
12. Perdidas diarias/semanales.
13. Racha de perdidas.
14. Liquidez y spread.
15. Seguridad de exchange/API.

### RF-RISK-002 - Circuit breakers

Deben existir circuit breakers para:

- Perdida diaria maxima.
- Perdida semanal maxima.
- Drawdown maximo.
- Racha de perdidas.
- Numero maximo de trades por dia.
- Volatilidad extrema.
- Error repetido de API.
- Desviacion fuerte de precio.
- Fallo de datos.

### RF-RISK-003 - Reduccion dinamica de tamano

Si el mercado tiene alta volatilidad o la estrategia tiene baja confianza, el sistema debe reducir automaticamente el tamano sugerido o rechazar la operacion.

### RF-RISK-004 - Riesgo por correlacion

El sistema debe calcular correlacion entre activos del portfolio. Si BTC, ETH y SOL estan altamente correlacionados, el sistema debe tratar la exposicion como concentrada.

### RF-RISK-005 - Registro de rechazos

Todo rechazo de riesgo debe registrarse con:

- Fecha/hora UTC.
- Senal original.
- Regla que bloqueo.
- Estado del portfolio.
- Contexto de mercado.
- Mensaje explicativo.

### Criterios de aceptacion

- No se aprueban operaciones sin stop-loss cuando la politica lo exige.
- Se bloquean operaciones que superen exposicion maxima.
- Se bloquea la apertura de posiciones con `KILL_SWITCH=true`.
- Se registra cada decision de riesgo.

---

## 6.5 Deteccion de Regimen de Mercado

### Objetivo

Ajustar la exposicion segun condiciones de mercado.

### Ubicacion propuesta

```text
app/market/
  regime_detector.py
  volatility.py
  liquidity.py
  correlations.py
  btc_dominance.py
```

### RF-MKT-001 - Clasificador de regimen

El sistema debe clasificar el mercado en:

- `strong_bull`
- `bull`
- `sideways`
- `bear`
- `strong_bear`
- `high_volatility`
- `panic`
- `euphoria`
- `risk_on`
- `risk_off`

### RF-MKT-002 - Indicadores para regimen

Debe considerar:

- Tendencia BTC.
- Tendencia ETH.
- Volatilidad realizada.
- Volumen relativo.
- Drawdown desde maximos recientes.
- Correlacion entre activos.
- Distancia a medias moviles relevantes.
- RSI multi-timeframe.
- Liquidez/spread.

### RF-MKT-003 - Uso del regimen en riesgo

El regimen debe afectar:

- Tamano de posicion.
- Activos permitidos.
- Estrategias permitidas.
- Nivel de cash minimo.
- Activacion de circuit breakers.

### Criterios de aceptacion

- El dashboard muestra el regimen actual.
- Las decisiones de riesgo guardan el regimen usado.
- El sistema puede bloquear nuevas entradas en `panic` o `high_volatility`.

---

## 6.6 Portfolio Management

### Objetivo

Gestionar inversiones como cartera, no solo como trades aislados.

### Ubicacion propuesta

```text
app/portfolio/
  allocation.py
  performance.py
  rebalancing.py
  exposure.py
  snapshots.py
```

### RF-PORT-001 - Vista consolidada de portfolio

El sistema debe calcular:

- Valor total.
- Cash disponible.
- Exposicion total.
- Exposicion por activo.
- Exposicion por categoria.
- PnL realizado.
- PnL no realizado.
- Drawdown actual.
- Drawdown maximo.
- Performance diaria/semanal/mensual.

### RF-PORT-002 - Rebalanceo

El sistema debe permitir reglas de rebalanceo:

- Por umbral.
- Por frecuencia.
- Por desviacion frente a objetivo.
- Por reduccion de riesgo.

### RF-PORT-003 - Cash management

Debe existir un minimo de cash/reserva no operativa. Si el cash cae por debajo del minimo, se deben bloquear nuevas entradas.

### RF-PORT-004 - Snapshots historicos

El sistema debe guardar snapshots periodicos de portfolio para calcular performance real.

### Criterios de aceptacion

- El portfolio se reconstruye desde trades y posiciones.
- Los snapshots permiten visualizar evolucion historica.
- Las exposiciones se usan en el motor de riesgo.

---

## 6.7 Paper Trading Profesional

### Objetivo

Simular operacion real con suficiente fidelidad antes de usar capital real.

### RF-PT-001 - Persistencia completa

El paper trading debe persistir:

- Ordenes simuladas.
- Trades ejecutados.
- Posiciones.
- Snapshots de portfolio.
- Senales rechazadas.
- Senales aprobadas.
- Diferencia entre precio teorico y precio ejecutado.

### RF-PT-002 - Modelo de ejecucion realista

Debe simular:

- Comisiones.
- Slippage.
- Spread.
- Rechazos por liquidez.
- Desviacion de precio.
- Latencia basica.

### RF-PT-003 - Comparacion backtest vs paper

Debe comparar resultados esperados contra resultados simulados reales:

- Diferencia de retorno.
- Diferencia de drawdown.
- Diferencia de win rate.
- Diferencia de profit factor.
- Diferencia de cantidad de operaciones.

### RF-PT-004 - Duracion minima

Una estrategia debe permanecer en paper trading por un periodo minimo configurable antes de ser candidata a real manual.

### Criterios de aceptacion

- El cierre y reapertura del dashboard no pierde estado.
- Todas las operaciones paper quedan registradas.
- Las metricas se calculan sobre datos persistidos.
- El sistema informa si una estrategia se degrada frente al backtest.

---

## 6.8 Decision Log y Auditoria

### Objetivo

Registrar de forma completa y consultable el proceso de decision.

### Ubicacion propuesta

```text
app/governance/
  decision_log.py
  approvals.py
  audit_trail.py
  change_control.py
```

### RF-GOV-001 - Registro de decision

Cada decision debe registrar:

- `decision_id`
- timestamp UTC.
- tipo: `signal`, `policy_check`, `risk_check`, `safety_check`, `approval`, `execution`, `rejection`.
- activo.
- estrategia.
- timeframe.
- modo.
- input original.
- resultado.
- motivo.
- usuario o sistema que decidio.
- version de configuracion.
- version de estrategia.

### RF-GOV-002 - Aprobacion humana

Para `real_manual`, debe existir una aprobacion explicita con:

- Usuario aprobador.
- Fecha/hora.
- Resumen de la propuesta.
- Riesgos principales.
- Tamano de posicion.
- Stop-loss.
- Motivo de aprobacion.

### RF-GOV-003 - Control de cambios

Cambios en parametros criticos deben quedar registrados:

- Politica de inversion.
- Limites de riesgo.
- Whitelist/blacklist.
- Parametros de estrategia.
- Activacion/desactivacion de estrategia.
- Cambio de modo operativo.
- Cambio de kill switch.

### Criterios de aceptacion

- Se puede reconstruir por que se tomo o rechazo una decision.
- Todo cambio critico tiene autor, fecha y diff/resumen.
- El dashboard permite consultar auditoria.

---

## 6.9 Dashboard Ejecutivo y Operativo

### Objetivo

Permitir seguimiento claro del sistema, portfolio, estrategias, riesgo y operaciones.

### RF-DASH-001 - Vista Overview

Debe mostrar:

- Estado del sistema.
- Modo actual.
- Kill switch.
- Valor de portfolio.
- Cash.
- Exposicion total.
- Drawdown actual.
- Alertas criticas.
- Ultimas decisiones.

### RF-DASH-002 - Vista Risk

Debe mostrar:

- Limites configurados.
- Uso actual de limites.
- Circuit breakers activos.
- Riesgos por activo.
- Riesgos por estrategia.
- Exposicion correlacionada.

### RF-DASH-003 - Vista Strategies

Debe mostrar:

- Estrategias disponibles.
- Estado de promocion.
- Performance historica.
- Performance paper.
- Reglas incumplidas.
- Recomendacion de promocion o pausa.

### RF-DASH-004 - Vista Decisions/Audit

Debe mostrar:

- Senales generadas.
- Senales aprobadas.
- Senales rechazadas.
- Motivos de rechazo.
- Cambios de configuracion.
- Aprobaciones humanas.

### RF-DASH-005 - Vista Market Regime

Debe mostrar:

- Regimen actual.
- Indicadores usados.
- Volatilidad.
- Correlacion.
- Activos en vigilancia.
- Alertas macro/mercado.

### Criterios de aceptacion

- Un operador puede entender el estado del sistema en menos de 1 minuto.
- Toda alerta critica es visible en Overview.
- Toda estrategia tiene estado y evidencia visible.

---

## 6.10 IA y Asistente Analitico

### Objetivo

Incorporar IA como apoyo de analisis, explicabilidad y mejora continua, sin delegar ejecucion.

### RF-AI-001 - Explicacion de senales

La IA debe explicar senales en lenguaje claro:

- Que activo.
- Que estrategia.
- Que indicadores participaron.
- Que contexto de mercado existe.
- Que riesgos principales hay.
- Por que fue aprobada o rechazada.

### RF-AI-002 - Analisis del journal

La IA debe detectar patrones de comportamiento:

- Sobreoperacion.
- Operar tras perdidas.
- Ignorar senales del sistema.
- Entradas fuera de politica.
- Cambios impulsivos de parametros.

### RF-AI-003 - Generacion de hipotesis

La IA puede proponer nuevas hipotesis de estrategia, pero deben entrar como `draft` y pasar por todo el proceso de validacion.

### RF-AI-004 - Prohibiciones

La IA no puede:

- Ejecutar ordenes.
- Aprobar operaciones.
- Cambiar limites.
- Cambiar politica.
- Activar trading real.
- Agregar activos a whitelist sin aprobacion.

### RF-AI-005 - Trazabilidad de prompts

Toda respuesta de IA usada para decision debe guardar:

- Prompt.
- Respuesta.
- Modelo usado.
- Fecha/hora.
- Contexto enviado.
- Version de datos.

### Criterios de aceptacion

- Una recomendacion de IA nunca genera una orden directamente.
- Las respuestas de IA quedan registradas si influyen en analisis.
- El dashboard diferencia claramente senal cuantitativa, decision de riesgo y explicacion IA.

---

## 6.11 Seguridad y Gestion de Secretos

### Objetivo

Evitar exposicion de claves, credenciales y permisos peligrosos.

### RF-SEC-001 - Secretos fuera del repositorio

Las API keys, tokens y secretos deben residir fuera del codigo y del repositorio.

### RF-SEC-002 - Validacion de permisos Binance

El sistema debe rechazar claves que tengan:

- Permisos de retiro.
- Permisos innecesarios.
- Alcance mayor al requerido.

### RF-SEC-003 - Principio de menor privilegio

Cada componente debe acceder solo a los secretos y recursos estrictamente necesarios.

### RF-SEC-004 - Rotacion de secretos

Debe existir procedimiento documentado para rotar:

- Binance API key.
- Binance API secret.
- Telegram bot token.
- Otros tokens externos.

### RF-SEC-005 - Fallar cerrado

Ante error de configuracion, error de permisos o datos incompletos, el sistema debe rechazar ejecucion.

### RF-SEC-006 - Proteccion de datos locales

La base SQLite local debe excluirse de Git y debe considerarse sensible si contiene operaciones, portfolio o historico de decisiones.

### Criterios de aceptacion

- No hay secretos commiteados.
- Las pruebas de seguridad detectan patrones de secretos.
- Una API key con retiro activo bloquea el sistema.
- Los logs no imprimen secretos.

---

## 6.12 Alertas y Monitoreo

### Objetivo

Notificar eventos relevantes antes de que se conviertan en incidentes.

### RF-ALERT-001 - Alertas criticas

Deben existir alertas para:

- Kill switch activado/desactivado.
- Drawdown superior a umbral.
- Perdida diaria/semanal.
- Error de API repetido.
- Datos incompletos.
- Estrategia degradada.
- Operacion rechazada por riesgo.
- Intento de operar activo no permitido.
- API key peligrosa.

### RF-ALERT-002 - Canales

Canales iniciales:

- Dashboard.
- Logs.
- Telegram opcional.
- Archivo local de eventos.

### RF-ALERT-003 - Severidad

Severidades:

- `info`
- `warning`
- `high`
- `critical`

### Criterios de aceptacion

- Una alerta critica aparece en Overview.
- Las alertas quedan persistidas.
- Las alertas no exponen secretos.

---

## 6.13 Calidad, Testing y CI

### Objetivo

Mantener calidad tecnica suficiente para un sistema financiero privado.

### RF-QA-001 - Quality gate obligatorio

Antes de merge o release debe ejecutarse:

```bash
python -m quality.quality_agent --check-all
```

### RF-QA-002 - Tests minimos

Deben existir pruebas para:

- Politica de inversion.
- Whitelist/blacklist.
- Promocion de estrategias.
- Backtesting.
- Riesgo.
- Paper trading.
- Decision log.
- Safety checks.
- Configuracion.
- Dashboard core, cuando sea posible.

### RF-QA-003 - Cobertura minima

Objetivo inicial:

- 70% en modulos core.
- 80% en riesgo, politica y ejecucion.
- 90% en safety checks.

### RF-QA-004 - Validacion de datos

El sistema debe validar:

- Continuidad de velas.
- Duplicados.
- Orden temporal.
- Valores negativos o nulos invalidos.
- Gaps de mercado.
- Desfase de timestamps.

### RF-QA-005 - Limpieza de dependencias

Debe unificarse la gestion de dependencias:

- Evitar duplicados en `requirements.txt`.
- Resolver version unica de `numpy`.
- Alinear `requirements.txt` con `pyproject.toml`.
- Incluir dependencias reales del dashboard y desarrollo.

### Criterios de aceptacion

- El quality agent pasa en main.
- Los tests pasan localmente.
- No hay dependencias duplicadas o contradictorias.
- Los modulos criticos tienen tests.

---

## 7. Requerimientos no funcionales

### RNF-001 - Seguridad por defecto

El sistema debe iniciar en modo seguro:

```yaml
app:
  mode: analysis
  kill_switch: true
trading:
  allow_real_trading: false
  allow_futures: false
  allow_leverage: false
```

### RNF-002 - Trazabilidad

Toda decision critica debe ser persistente, consultable y exportable.

### RNF-003 - Reproducibilidad

Todo backtest debe poder reproducirse con:

- Dataset.
- Version de estrategia.
- Parametros.
- Costos.
- Rango temporal.
- Version de configuracion.

### RNF-004 - Modularidad

Los modulos deben mantenerse desacoplados:

- Datos no debe depender de dashboard.
- Estrategias no deben ejecutar ordenes.
- Riesgo no debe modificar estrategias.
- IA no debe modificar politica.
- Dashboard no debe contener reglas de negocio criticas.

### RNF-005 - Observabilidad

Debe haber logs claros, estructurados y sin secretos para:

- Descarga de datos.
- Backtesting.
- Senales.
- Riesgo.
- Politica.
- Paper trading.
- Seguridad.
- Alertas.

### RNF-006 - Simplicidad operativa

Los comandos principales deben funcionar desde raiz del proyecto y estar documentados.

### RNF-007 - Fallo seguro

Ante error inesperado, el sistema debe:

- Rechazar ejecucion.
- Registrar error.
- Notificar si es critico.
- No abrir nuevas posiciones.

---

## 8. Modelo de datos propuesto

### 8.1 Nuevas tablas sugeridas

```sql
CREATE TABLE IF NOT EXISTS investment_policy_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    content_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT DEFAULT 'system'
);
```

```sql
CREATE TABLE IF NOT EXISTS strategy_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    hypothesis TEXT DEFAULT '',
    parameters_json TEXT DEFAULT '{}',
    allowed_symbols_json TEXT DEFAULT '[]',
    allowed_timeframes_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(name, version)
);
```

```sql
CREATE TABLE IF NOT EXISTS strategy_promotion_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_json TEXT DEFAULT '{}',
    approved_by TEXT DEFAULT 'system',
    created_at TEXT NOT NULL
);
```

```sql
CREATE TABLE IF NOT EXISTS decision_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL UNIQUE,
    decision_type TEXT NOT NULL,
    symbol TEXT,
    strategy_name TEXT,
    timeframe TEXT,
    mode TEXT NOT NULL,
    approved INTEGER NOT NULL,
    reason TEXT NOT NULL,
    input_json TEXT DEFAULT '{}',
    output_json TEXT DEFAULT '{}',
    policy_version TEXT,
    strategy_version TEXT,
    created_at TEXT NOT NULL
);
```

```sql
CREATE TABLE IF NOT EXISTS market_regime_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    regime TEXT NOT NULL,
    volatility REAL,
    trend_score REAL,
    momentum_score REAL,
    liquidity_score REAL,
    metadata_json TEXT DEFAULT '{}'
);
```

```sql
CREATE TABLE IF NOT EXISTS human_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_id TEXT NOT NULL UNIQUE,
    decision_id TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approved INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

---

## 9. Configuracion propuesta

Ejemplo de extension para `settings.yaml`:

```yaml
policy:
  enabled: true
  version: "1.0"
  min_cash_reserve_pct: 0.30
  max_total_crypto_exposure_pct: 0.60
  max_core_exposure_pct: 0.50
  max_systematic_exposure_pct: 0.30
  max_experimental_exposure_pct: 0.05
  require_whitelist: true
  prohibit_leverage: true
  prohibit_futures: true

asset_universe:
  whitelist:
    - symbol: BTCUSDT
      category: core
      enabled: true
      max_position_pct: 0.35
      min_history_days: 730
    - symbol: ETHUSDT
      category: core
      enabled: true
      max_position_pct: 0.25
      min_history_days: 730
  blacklist_categories:
    - meme
    - illiquid
    - new_listing

strategy_promotion:
  min_backtest_trades: 50
  min_profit_factor: 1.2
  min_sharpe_ratio: 1.0
  max_drawdown_pct: 20.0
  require_out_of_sample: true
  require_walk_forward: true
  min_paper_days: 30
  min_paper_trades: 20

market_regime:
  block_new_positions_on:
    - panic
    - high_volatility
  reduce_size_on:
    - risk_off
    - bear

execution:
  require_human_approval_for_real_manual: true
  require_ip_allowlist: true
  reject_api_withdraw_permission: true
```

---

## 10. Roadmap de implementacion

### Fase 1 - Orden, seguridad y deuda tecnica

Prioridad: alta.

Entregables:

- Limpiar dependencias.
- Corregir typo `vigilat_threshold`.
- Alinear `requirements.txt` y `pyproject.toml`.
- Crear `policy.yaml` o seccion `policy` en `settings.yaml`.
- Crear modulo `app/policy`.
- Crear tests de politica.
- Agregar tablas de politica y decision log.

### Fase 2 - Gobierno de estrategias

Prioridad: alta.

Entregables:

- Crear registry de estrategias.
- Crear estados de promocion.
- Crear reglas minimas de promocion.
- Crear eventos de promocion.
- Mostrar estrategias en dashboard.

### Fase 3 - Backtesting robusto

Prioridad: alta.

Entregables:

- Walk-forward testing.
- Out-of-sample.
- Monte Carlo.
- Sensibilidad de parametros.
- Reportes JSON/CSV.
- Comparador por regimen de mercado.

### Fase 4 - Riesgo avanzado y portfolio

Prioridad: alta.

Entregables:

- Portfolio consolidado.
- Correlaciones.
- Regimen de mercado.
- Cash management.
- Circuit breakers extendidos.
- Snapshots historicos.

### Fase 5 - Paper trading profesional

Prioridad: media/alta.

Entregables:

- Persistencia completa de ordenes simuladas.
- Registro de senales rechazadas.
- Modelo de ejecucion mas realista.
- Comparacion backtest vs paper.
- Alertas de degradacion.

### Fase 6 - Real manual controlado

Prioridad: media. No iniciar hasta completar fases anteriores.

Entregables:

- Aprobacion humana.
- Validacion de API key.
- Limites reforzados.
- Registro de orden real.
- Kill switch probado.
- Monto minimo inicial.

### Fase 7 - Real automatico limitado

Prioridad: futura. No iniciar sin evidencia fuerte.

Entregables:

- Automatizacion solo para estrategias promovidas.
- Limites extremadamente conservadores.
- Monitoreo continuo.
- Pausa automatica.
- Revision diaria obligatoria.

---

## 11. Prioridad de requerimientos

| Codigo | Requerimiento | Prioridad |
|---|---|---|
| RF-POL-001 | Politica global de inversion | Must |
| RF-POL-002 | Whitelist de activos | Must |
| RF-POL-003 | Blacklist de activos | Must |
| RF-STR-001 | Ficha de estrategia | Must |
| RF-STR-002 | Reglas minimas de promocion | Must |
| RF-BT-001 | Backtest con costos realistas | Must |
| RF-BT-002 | Walk-forward testing | Must |
| RF-BT-003 | Out-of-sample testing | Must |
| RF-RISK-001 | Evaluacion multicapa | Must |
| RF-RISK-002 | Circuit breakers | Must |
| RF-GOV-001 | Decision log | Must |
| RF-SEC-001 | Secretos fuera del repo | Must |
| RF-SEC-002 | Validacion permisos Binance | Must |
| RF-QA-001 | Quality gate obligatorio | Must |
| RF-MKT-001 | Clasificador de regimen | Should |
| RF-PORT-001 | Portfolio consolidado | Should |
| RF-PT-003 | Comparacion backtest vs paper | Should |
| RF-AI-001 | Explicacion de senales | Could |
| RF-AI-003 | Generacion de hipotesis | Could |
| RF-DASH-005 | Vista Market Regime | Could |

---

## 12. Definition of Done general

Un requerimiento se considera terminado cuando:

1. Tiene implementacion en codigo.
2. Tiene tests automatizados.
3. Esta documentado.
4. No rompe quality gates.
5. No introduce secretos ni datos sensibles.
6. Registra eventos criticos si corresponde.
7. Es visible en dashboard si corresponde.
8. Tiene criterios de aceptacion validados.
9. Mantiene modo seguro por defecto.
10. No habilita trading real sin controles.

---

## 13. Riesgos del proyecto

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Sobreajuste de estrategias | Alto | Walk-forward, out-of-sample, Monte Carlo |
| Automatizar demasiado pronto | Alto | Modos bloqueados, aprobacion humana |
| API key con permisos peligrosos | Critico | Validacion y rechazo automatico |
| Perdida por volatilidad extrema | Alto | Circuit breakers y regimen de mercado |
| Datos incompletos o corruptos | Alto | Validadores de continuidad |
| Dependencias inconsistentes | Medio | Unificar requirements/pyproject |
| IA generando falsas certezas | Alto | IA solo explicativa, sin ejecucion |
| Falta de trazabilidad | Alto | Decision log obligatorio |
| Operar activos iliquidos | Alto | Whitelist, liquidez minima, spread maximo |
| Error humano en parametros | Medio/Alto | Change control y aprobaciones |

---

## 14. Referencias de buenas practicas

Estas referencias deben usarse como guia conceptual, no como cumplimiento regulatorio formal:

- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- FINRA - Crypto Assets: https://www.finra.org/investors/investing/investment-products/crypto-assets
- OWASP Secrets Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- OWASP Application Security Verification Standard: https://owasp.org/www-project-application-security-verification-standard/

---

## 15. Nota final

CriptoLab debe evolucionar como una plataforma privada de investigacion, control y decision de inversion. El valor principal del sistema no esta en operar mas rapido, sino en operar con mayor disciplina, mejor evidencia, menor sesgo emocional, mayor trazabilidad y controles de riesgo fuertes.

La regla final del sistema debe ser:

> Si una operacion no puede explicarse, auditarse, limitarse y detenerse, no debe ejecutarse.
