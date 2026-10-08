# CLAUDE.md — Terminal Accounting

> Personal accounting application with a Flask REST API backend, a Textual TUI, and a React web frontend. Supports Jalali (Persian) calendar, multi-user authentication, and PostgreSQL persistence.

---

## Tech Stack Overview

### Backend — Python

| Component        | Technology                                      |
|------------------|-------------------------------------------------|
| Language         | Python 3.8+                                     |
| Web Framework    | Flask (Blueprint-based modular architecture)     |
| Database         | PostgreSQL via `psycopg2` (connection-pooled)    |
| API Docs         | Flasgger (Swagger / OpenAPI at `/apidocs/`)      |
| Calendar         | `jdatetime` — Jalali (Persian) calendar support  |
| Auth             | Custom session auth (`X-Username` header) + `pyotp` (TOTP) + `qrcode` |
| Env Management   | `python-dotenv`                                  |
| CLI Client       | `requests`-based CLI (`cli.py`)                  |

### TUI — Textual

| Component        | Technology                                      |
|------------------|-------------------------------------------------|
| Framework        | Textual (modern Python TUI framework)            |
| HTTP Client      | `requests`                                       |
| Features         | Sidebar navigation, data tables, Jalali date picker, custom widgets |

### Web Frontend — React

| Component        | Technology                                      |
|------------------|-------------------------------------------------|
| Language         | TypeScript 6.x                                   |
| Framework        | React 19.x                                       |
| Build Tool       | Vite 8.x                                         |
| Styling          | Tailwind CSS 4.x (via `@tailwindcss/vite`)       |
| UI Components    | Radix UI primitives + `lucide-react` icons       |
| Routing          | `react-router-dom` v7                            |
| State / Data     | `@tanstack/react-query` v5, React Context        |
| Tables           | `@tanstack/react-table` v8 + `@tanstack/react-virtual` |
| Forms            | `react-hook-form` v7 + `zod` validation          |
| Charts           | `recharts` v2                                    |
| i18n             | `i18next` + `react-i18next` + browser language detection |
| Jalali Calendar  | `jalaali-js`                                     |
| Animations       | `framer-motion` v12                              |
| Notifications    | `sonner` v2                                      |
| Command Palette  | `cmdk` v1                                        |
| QR Codes         | `qrcode.react`                                   |
| Linting          | ESLint 10.x (`eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`) |
| Path Aliases     | `@/` → `./src/`                                  |
| Dev Server Proxy | `/api` → `http://localhost:5000`                 |

### Build & Packaging

| Component        | Technology                                      |
|------------------|-------------------------------------------------|
| Standalone App   | PyInstaller (macOS `.app` bundle via `build.py` + `accounting.spec`) |
| Launcher         | `launcher.py` / `start.sh`                       |

### Testing

| Component        | Technology                                      |
|------------------|-------------------------------------------------|
| Test Framework   | `pytest` + `pytest-cov`                          |
| Test Location    | `tests/` directory                               |
| E2E Tests        | `tests/e2e/`                                     |
| Config           | `pytest.ini` (`-v --tb=short`)                   |

### Code Quality

| Component        | Technology                                      |
|------------------|-------------------------------------------------|
| Formatting       | `black`                                          |
| Linting          | `flake8`                                         |

### API Testing

| Component        | Technology                                      |
|------------------|-------------------------------------------------|
| Collections      | Postman collection (`postman/postman_collection.json`) |

---

## Project Structure

```
.
├── app/                    # Flask application
│   ├── models/             # Database models (user, category, source, transaction, budget)
│   ├── routes/             # API route blueprints (auth, transactions, wallets, budget, etc.)
│   ├── services/           # Business logic services
│   ├── utils/              # Utility modules
│   ├── config.py           # Flask config (Dev / Prod / Test environments)
│   └── extensions.py       # Flask extensions registry
├── services/               # Shared/domain services
│   ├── alert_service.py
│   ├── calendar_service.py
│   ├── check_service.py
│   ├── debt_service.py
│   ├── forecast_service.py
│   ├── installment_service.py
│   └── metadata_service.py
├── tui/                    # Textual TUI application
│   ├── app.py              # Main Textual app
│   ├── sidebar_menu.py     # Sidebar navigation
│   ├── calendar_view.py    # Financial calendar screen
│   ├── jalali_date_picker.py
│   └── config.py           # TUI configuration
├── web/                    # React web frontend
│   ├── src/
│   │   ├── api/            # API client layer
│   │   ├── components/     # Reusable UI components
│   │   ├── context/        # React context providers
│   │   ├── hooks/          # Custom React hooks
│   │   ├── i18n/           # Internationalization config
│   │   ├── keys/           # Query key factories
│   │   ├── lib/            # Shared utilities
│   │   ├── pages/          # Route page components
│   │   ├── router/         # React Router configuration
│   │   ├── schemas/        # Zod validation schemas
│   │   └── types/          # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts
├── tests/                  # pytest test suite
│   ├── e2e/                # End-to-end tests
│   └── conftest.py         # Shared test fixtures
├── data/                   # Data / seed files
├── docs/                   # Documentation (item analytics reports)
├── postman/                # Postman API collection
├── samples/                # Sample widget implementations
├── database.py             # PostgreSQL connection pool & schema init
├── main.py                 # TUI standalone entry point (calendar + forecast)
├── cli.py                  # CLI client for the REST API
├── run_api.py              # Flask API server launcher
├── run_tui.py              # TUI launcher
├── setup.py                # Package setup
├── build.py                # macOS standalone build script
├── accounting.spec          # PyInstaller spec file
├── requirements.txt         # Python dependencies
├── start.sh                 # One-command quick-start script
├── load_env.py              # Environment variable loader
├── pytest.ini               # Pytest configuration
└── .env / .env.staging / .env.production  # Environment files
```

---

## Database

- **Engine:** PostgreSQL
- **Driver:** `psycopg2-binary` with `SimpleConnectionPool` (1–20 connections)
- **Schema:** Auto-created on first run (`init_db()`)
- **Tables:** 11 tables — `users`, `categories`, `sources`, `transactions`, `budget_periods`, `budget_items`, `checks`, `installments`, `debts`, `wallets`, `settings`
- **Conventions:** All tables have `created_at`, `updated_at` (auto-updated via trigger), and `deleted_at` (soft delete)
- **Cursor:** `psycopg2.extras.RealDictCursor` (dict-like rows)

### Environment Variables

| Variable       | Default                       | Description             |
|----------------|-------------------------------|-------------------------|
| `DATABASE_URL` | *(none)*                      | Full connection string (takes precedence) |
| `DB_HOST`      | `localhost`                   | Database host           |
| `DB_PORT`      | `5432`                        | Database port           |
| `DB_NAME`      | `terminal_accounting_staging` | Database name           |
| `DB_USER`      | `postgres`                    | Database user           |
| `DB_PASSWORD`  | *(empty)*                     | Database password       |
| `APP_ENV`      | `development`                 | Environment (`development` / `staging` / `production`) |
| `FLASK_DEBUG`  | `True`                        | Flask debug mode        |
| `BASE_URL`     | `http://127.0.0.1:5000`       | API base URL            |

---

## Running the Application

### Quick Start (all-in-one)
```bash
./start.sh
```

### Manual — API Server
```bash
source venv/bin/activate
python run_api.py
# API at http://127.0.0.1:5000
# Swagger docs at http://127.0.0.1:5000/apidocs/
```

### Manual — TUI
```bash
source venv/bin/activate
python run_tui.py
```

### Manual — Web Frontend
```bash
cd web
npm install    # or yarn / bun
npm run dev
# Frontend at http://localhost:5173 (proxies /api → localhost:5000)
```

### CLI Client
```bash
python cli.py <command>
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run E2E tests only
pytest tests/e2e/
```

---

## Code Style

- **Python:** Formatted with `black`, linted with `flake8`
- **TypeScript/React:** Linted with ESLint (`npm run lint` / `yarn lint`)
- **Type checking:** `npm run typecheck` / `yarn typecheck`

---

## Build Standalone (macOS)

```bash
python build.py
# Or via PyInstaller directly:
pyinstaller accounting.spec
```

---

## Key Conventions

1. **Jalali calendar** is used throughout for date display and input (backend: `jdatetime`, frontend: `jalaali-js`).
2. **Currency** is displayed in Toman with locale-aware formatting.
3. **Soft deletes** — records are never hard-deleted; `deleted_at` is set instead.
4. **Blueprint architecture** — Flask routes are organized as blueprints under `app/routes/`.
5. **Service layer** — Business logic lives in `app/services/` and `services/`, separate from route handlers.
6. **Path alias** — Web frontend uses `@/` → `./src/` for clean imports.
7. **Dev proxy** — Vite proxies `/api/*` requests to the Flask backend at `localhost:5000`.
