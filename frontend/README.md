# Syntara Frontend

## Commands

- `npm run dev`
- `npm run build`
- `npm run lint`

## API Wiring

- The frontend calls `/api` by default.
- In local Vite development, `/api` is proxied to `VITE_BACKEND_TARGET`.
- `VITE_BACKEND_TARGET` defaults to `http://127.0.0.1:8888`.
- If you need the browser to call a different backend directly, set `VITE_API_BASE` to either:
  - `http://127.0.0.1:18888`
  - `http://127.0.0.1:18888/api`

## Typical Local Setup

```bash
SYNTARA_PORT=18888 ./start.sh
```

That keeps the backend off port `8000` and lets the frontend keep using the dev proxy without source changes.
