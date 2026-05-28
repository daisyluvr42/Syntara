# Stability Fixes Design

## Goals

- Restore a green frontend build.
- Remove front/backend API drift around provider types and embedding config payloads.
- Fix filtered literature totals so the UI reflects the actual query.
- Stop hardcoding the backend to `127.0.0.1:8888` inside frontend source.
- Keep the backend easy to run persistently on a non-`8000` port.

## Approved Approach

- Frontend API calls default to same-origin `/api`.
- Vite dev uses a configurable proxy target instead of hardcoded frontend source URLs.
- Runtime ports come from environment variables:
  - `SYNTARA_HOST`
  - `SYNTARA_PORT`
  - `FRONTEND_HOST`
  - `FRONTEND_PORT`
  - `VITE_BACKEND_TARGET`
- Remove dead frontend files that are no longer part of the app but still break TypeScript builds.
- Fix the backend literature count query to apply the same tag filter as the list query.

## Non-Goals

- No deployment redesign.
- No large refactor of API client structure.
- No search/filter behavior changes beyond the broken total count.
