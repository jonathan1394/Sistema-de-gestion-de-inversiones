# Plan de Validación y Cierre de Brechas API ↔ Frontend

## Objetivo

Cerrar sistemáticamente las brechas entre lo que la API FastAPI expone y lo que el frontend Next.js realmente consume, priorizando por impacto operativo.

---

## Fase 0 — Auditoría Base (diagnóstico ya completado)

| Área | Endpoint | Estado | Gap |
|---|---|---|---|
| System | `GET /system/health` | OK | — |
| System | `GET /system/status` | ❌ | Sin UI |
| Config | `GET /config` | Parcial | Solo 2 campos usados de ~30 |
| Market | `GET /market/price/{symbol}` | Parcial | No se usa `interval` desde UI externa |
| Market | `GET /market/candles/{symbol}/{interval}` | Parcial | No expone `start_ms`, `end_ms`, `desc` |
| Market | `GET /market/summary` | Parcial | Símbolos fijos en UI |
| Portfolio | `GET /portfolio/state` | OK | — |
| Portfolio | `GET /portfolio/trades` | Parcial | Sin filtro `symbol`, paginación fija |
| Portfolio | `GET /portfolio/snapshots` | Parcial | Paginación fija |
| Risk | `GET /risk/limits` | Parcial | Datos crudos sin acción |
| Risk | `GET /risk/status` | ❌ | Sin UI |
| Risk | `GET /risk/circuit-breakers` | ❌ | Sin UI |
| Risk | `POST /risk/evaluate` | Parcial | No envía `portfolio`, `stop_loss_price` |
| Backtest | `GET /backtest/strategies` | OK | — |
| Backtest | `POST /backtest/run` | Parcial | Sin flujo guiado por estrategia |
| Prospecting | `GET /prospecting/prospects` | ❌ | Sin vista de prospects persistidos |
| Prospecting | `POST /prospecting/scan` | Parcial | Solo scan global |
| Prospecting | `GET /prospecting/ranking` | OK | — |
| Prospecting | `GET /prospecting/decision/{symbol}` | Parcial | No usa `interval` |
| Prospecting | `POST /prospecting/prospects/status` | ❌ | Sin acción UI |
| Prospecting | `POST /prospecting/prospects/add` | ❌ | Sin acción UI |
| Decisions | `GET /decisions` | Parcial | Sin filtros `symbol`, `approved_only`, `rejected_only`, paginación real |
| Alerts | `GET /alerts/history` | OK | — |
| Alerts | `GET /alerts/rules` | Parcial | Solo lectura |
| Alerts | `POST /alerts/rules` | ❌ | No editable desde UI |
| Alerts | `POST /alerts/history/clear` | OK | — |

---

## Fase 1 — Reparar flujos rotos (Alta prioridad)

### 1.1 Leer `searchParams` en páginas Backtest y Risk

**Archivos destino:**
- `frontend/src/app/backtest/page.tsx`
- `frontend/src/app/risk/page.tsx`
- `frontend/src/app/backtest/runner.tsx`
- `frontend/src/app/risk/risk-evaluator.tsx`

**Qué hacer:**
1. En `page.tsx` de backtest, leer `searchParams?.symbol` y pasarlo como prop inicial a `BacktestRunner`.
2. En `runner.tsx`, usar esa prop como `initialSymbol` del estado.
3. En `page.tsx` de risk, leer `searchParams?.symbol` y pasarlo como prop inicial a `RiskEvaluator`.
4. En `risk-evaluator.tsx`, usar esa prop como `initialSymbol`.

**Validación:**
- Ir a `/assets/BTCUSDT`, click "Backtest BTCUSDT" → la URL cambia a `/backtest?symbol=BTCUSDT` y el campo Symbol se prellena.
- Lo mismo para Risk.

**Archivos:**
- `frontend/src/app/backtest/page.tsx`
- `frontend/src/app/backtest/runner.tsx`
- `frontend/src/app/risk/page.tsx`
- `frontend/src/app/risk/risk-evaluator.tsx`

### 1.2 Completar módulo Prospecting

**Nuevos componentes/archivos:**
- `frontend/src/app/prospects/prospects-list.tsx` — tabla con prospects desde `GET /prospecting/prospects`
- Filtros en `frontend/src/app/prospects/prospecting-filters.tsx` — status, min_score
- Botón "Add prospect" → llama a `POST /prospecting/prospects/add`
- En la misma fila de la tabla, botón para cambiar status → `POST /prospecting/prospects/status`
- En `prospecting-actions.tsx`, agregar input para scan por símbolo + intervalo

**Endpoints a conectar:**
- `GET /prospecting/prospects?page=1&limit=50&status=watching&min_score=0.5`
- `POST /prospecting/prospects/add` con body `{symbol, interval?, notes?}`
- `POST /prospecting/prospects/status` con body `{symbol, interval, status}`
- `POST /prospecting/scan` con body opcional `{symbol, interval}`

**Validación:**
- La página Prospects muestra no solo ranking sino también la tabla real de prospects.
- Se puede agregar un símbolo manualmente.
- Se puede cambiar el estado de un prospect.
- Scan puede ejecutarse para un símbolo específico.

### 1.3 Habilitar edición de reglas de Alertas

**Archivos destino:**
- `frontend/src/app/alerts/rules-editor.tsx` — nuevo componente
- `frontend/src/app/alerts/page.tsx` — integrar editor
- `frontend/src/app/alerts/alerts-actions.tsx` — agregar botón "Save rules"

**Qué hacer:**
1. Leer reglas actuales con `GET /alerts/rules`.
2. Renderizar un editor JSON o formulario simple.
3. Guardar con `POST /alerts/rules`.
4. Refrescar la vista tras guardar.

**Validación:**
- Editar reglas, guardar, recargar página → los cambios persisten.
- El archivo `data/alert_rules.json` se crea en backend.

---

## Fase 2 — Completar parámetros (Media prioridad)

### 2.1 Agregar filtros y paginación en Decisions

**Archivos destino:**
- `frontend/src/app/decisions/page.tsx`
- `frontend/src/app/decisions/decisions-actions.tsx`

**Qué hacer:**
1. Agregar `input` para filtrar por `symbol`.
2. Agregar checkbox para `approved_only` y `rejected_only`.
3. Agregar paginación (anterior/siguiente) usando `page`.
4. Los filtros deben reflejarse en la URL (`searchParams`) para permitir compartir enlaces.

**Endpoint:**
`GET /decisions?page=1&limit=50&symbol=BTCUSDT&approved_only=true`

### 2.2 Agregar filtro por símbolo y paginación real en Portfolio trades

**Archivos destino:**
- `frontend/src/app/portfolio/page.tsx`

**Qué hacer:**
1. Leer `searchParams?.symbol` para prefiltrar.
2. Agregar `input` para filtrar por símbolo.
3. Agregar controles de paginación.
4. Reflejar filtros en URL.

### 2.3 Agregar `start_ms` / `end_ms` / `desc` en Market candles

**Archivos destino:**
- `frontend/src/app/market/market-controls.tsx`
- `frontend/src/app/market/page.tsx`

**Qué hacer:**
1. Agregar inputs para `start_ms` y `end_ms` (timestamps en ms) o un date picker simple.
2. Agregar checkbox para orden descendente.
3. Pasar los parámetros a la llamada `GET /market/candles/{symbol}/{interval}`.

### 2.4 Pasar `interval` en `decision/{symbol}` desde Asset Detail

**Archivo destino:**
- `frontend/src/app/assets/[symbol]/page.tsx`

**Qué hacer:**
1. Agregar un selector de intervalo junto al precio.
2. Pasar `interval` como query param a `GET /prospecting/decision/{symbol}`.

---

## Fase 3 — Exponer endpoints informativos (Baja prioridad)

### 3.1 Mostrar `system/status` en Home o Overview

**Archivos destino:**
- `frontend/src/app/overview/page.tsx`
- o crear sección en `frontend/src/app/page.tsx`

**Qué hacer:**
1. Llamar `GET /system/status`.
2. Renderizar timestamp del servidor.

### 3.2 Agregar sección Risk Status y Circuit Breakers en página Risk

**Archivos destino:**
- `frontend/src/app/risk/page.tsx`

**Qué hacer:**
1. Llamar `GET /risk/status` y `GET /risk/circuit-breakers`.
2. Mostrar estado en cards informativos.

### 3.3 Expandir uso de Config en Overview

**Archivo destino:**
- `frontend/src/app/overview/page.tsx`

**Qué hacer:**
1. Mostrar más campos de la respuesta `/config`: fees, riesgo, trading, timeframes.
2. Agregar secciones colapsables para no saturar la vista inicial.

---

## Fase 4 — Pruebas de validación

Por cada cambio ejecutar:

1. **TypeScript**: `npx tsc --noEmit` en `frontend/`
2. **Lint**: `npx eslint .` en `frontend/`
3. **Build**: `npx next build` en `frontend/`
4. **Backend lint**: `ruff check app/` en raíz
5. **Backend types**: `mypy app/` en raíz

---

## Fase 5 — Verificación final

1. Recorrer cada pantalla del Nav:
   - Home, Overview, Market, Prospects, Ranking, Backtest, Portfolio, Risk, Alerts, Decisions
2. Para cada pantalla, confirmar que:
   - No hay errores en consola del navegador.
   - La respuesta de la API se renderiza correctamente.
   - Todos los parámetros relevantes tienen control en UI.
   - La paginación funciona cuando aplica.
   - Los filtros persisten en la URL.
3. Probar flujo completo:
   - Overview → Market → Prospects → Ranking → Asset detail → Backtest → Risk
4. Verificar que no haya llamadas a endpoints que no existan en la API.

---

## Resumen de archivos a modificar/crear

| Archivo | Acción | Prioridad |
|---|---|---|
| `frontend/src/app/backtest/page.tsx` | Modificar | Alta |
| `frontend/src/app/backtest/runner.tsx` | Modificar | Alta |
| `frontend/src/app/risk/page.tsx` | Modificar | Alta |
| `frontend/src/app/risk/risk-evaluator.tsx` | Modificar | Alta |
| `frontend/src/app/prospects/prospects-list.tsx` | **Crear** | Alta |
| `frontend/src/app/prospects/prospecting-filters.tsx` | **Crear** | Alta |
| `frontend/src/app/prospects/page.tsx` | Modificar | Alta |
| `frontend/src/app/prospects/prospecting-actions.tsx` | Modificar | Alta |
| `frontend/src/app/alerts/rules-editor.tsx` | **Crear** | Alta |
| `frontend/src/app/alerts/page.tsx` | Modificar | Alta |
| `frontend/src/app/alerts/alerts-actions.tsx` | Modificar | Alta |
| `frontend/src/app/decisions/page.tsx` | Modificar | Media |
| `frontend/src/app/decisions/decisions-actions.tsx` | Modificar | Media |
| `frontend/src/app/portfolio/page.tsx` | Modificar | Media |
| `frontend/src/app/market/market-controls.tsx` | Modificar | Media |
| `frontend/src/app/market/page.tsx` | Modificar | Media |
| `frontend/src/app/assets/[symbol]/page.tsx` | Modificar | Media |
| `frontend/src/app/overview/page.tsx` | Modificar | Baja |
| `frontend/src/app/page.tsx` | Modificar | Baja |

---

## Orden de ejecución recomendado

```
Paso 1  → Fase 1.1 (flujos rotos backtest + risk)
Paso 2  → Fase 1.2 (prospecting completo)
Paso 3  → Fase 1.3 (alerts editor)
Paso 4  → Fase 2.1 (decisions filters)
Paso 5  → Fase 2.2 (portfolio filters + paginación)
Paso 6  → Fase 2.3 (market candles params)
Paso 7  → Fase 2.4 (asset detail interval)
Paso 8  → Fase 3 (endpoints informativos)
Paso 9  → Fase 4 (pruebas)
Paso 10 → Fase 5 (verificación final)
```

Cada paso debe completarse y verificarse antes de pasar al siguiente.
