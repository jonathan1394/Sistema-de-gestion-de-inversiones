# CriptoLab Web

Frontend Next.js para CriptoLab. Consume la API FastAPI del proyecto mediante `frontend/src/lib/api.ts`.

## Requisitos

- Node.js 20+
- API FastAPI corriendo localmente o accesible por red

## Desarrollo

```bash
npm install
npm run dev
```

Variable de entorno principal:

```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api/v1
```

## Páginas actuales

- `/` estado básico de API
- `/overview`
- `/market`
- `/prospects`
- `/ranking`
- `/backtest`
- `/portfolio`
- `/risk`
- `/alerts`
- `/decisions`
- `/logs`
- `/assets/[symbol]`

## Integración

- Lecturas: `apiGet()`
- Mutaciones: `apiPost()`, `apiPut()`, `apiDelete()`
- Todas las llamadas pasan por `frontend/src/lib/api.ts`

## Checks

```bash
npm run lint
```
