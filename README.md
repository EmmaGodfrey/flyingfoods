# Flying Foods Restaurant & Inventory System

Operations system for kitchen fulfilment, waiter service, multi-location
inventory, procurement, wastage, recipe management, and Pastel stock
synchronisation. Cashiering and payments remain in the existing POS.

## Stack

- Django 5, Django REST Framework, PostgreSQL, Redis, Celery, and Channels
- React 18, TypeScript, Vite, React Query, and Zustand
- Docker Compose for local PostgreSQL, Redis, Mailpit, backend, workers, and frontend

## Repository

- `backend/` — API, WebSockets, background jobs, and domain logic
- `frontend/` — role-based web application
- `docs/` — business requirements, system overview, and compliance audit
- `specs/` — detailed functional specification and API/data-model decisions

## Quick start

1. Copy `backend/.env.example` to `backend/.env`.
2. Start infrastructure: `docker compose up -d postgres redis mailpit`.
3. Install and run the backend:

   ```powershell
   cd backend
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   python manage.py migrate
   python manage.py seed_demo
   python manage.py runserver
   ```

4. Install and run the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

The API defaults to `http://localhost:8000`; the frontend defaults to
`http://localhost:5173`; Mailpit is available at `http://localhost:8025`.

## Verification

```powershell
cd backend
pytest
python manage.py makemigrations --check --dry-run

cd ..\frontend
npm run build
```

See [docs/BRD_COMPLIANCE.md](docs/BRD_COMPLIANCE.md) for implemented and
outstanding business requirements.

Development-server CI/CD setup is documented in
[docs/DEPLOYMENT_DEV.md](docs/DEPLOYMENT_DEV.md).

Team domain ownership and issue workflow are documented in
[docs/TEAM_OWNERSHIP.md](docs/TEAM_OWNERSHIP.md).
