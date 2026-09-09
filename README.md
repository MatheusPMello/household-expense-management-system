# HomeLedger — Shared Household Expense Management System

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=coverage)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)

> A modern, ledger-based expense management platform built for multi-resident households. Engineered with integer-cent precision, deterministic expense allocation, and auditable financial projections.

🚀 **Live Production Application:** [HomeLedger - Shared Household Expense Management](https://household-expense-management-system.vercel.app/login)

---

## 1. Project Overview

HomeLedger is a full-stack web application designed to eliminate financial ambiguity and accounting friction in shared living environments (e.g., roommates, couples, co-housing communities).

Unlike conventional expense-sharing trackers that store balances as directly mutable fields or rely on floating-point arithmetic, HomeLedger models household finances through a **ledger projection pattern**:
- **Zero Floating-Point Drift:** Every currency value is stored and calculated as an exact integer number of cents.
- **Event-Driven Balance Projection:** Current resident balances are dynamically evaluated against an immutable stream of expense splits, contribution payments, and audited debt waivers.
- **Deterministic Penny-Perfect Splits:** Remainder cents are distributed according to reproducible allocation strategies (equal, percentage, exact, weighted) without lost fractions.
- **Multi-Tenant Scoping:** Built-in household isolation with role-based access control (`ADMIN` and `MEMBER`).

---

## 2. Cloud & Deployment Architecture

HomeLedger is deployed across a decoupled, cloud-native infrastructure optimized for high availability, low latency, and serverless database scalability.

```text
  [ User Browser / Client ]
             │
             │ HTTPS / Global CDN
             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  Frontend Layer: Vercel                                     │
  │  • React 18 + Vite + TypeScript Single Page Application     │
  │  • Tailwind CSS & TanStack Query v5                         │
  │  • Edge CDN caching & client-side route rewrites            │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 │ REST API / JWT Bearer
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  Backend API Layer: Render                                  │
  │  • Python 3.13 + FastAPI Asynchronous Web Service           │
  │  • Pydantic v2 schemas & SQLAlchemy 2.0 Async ORM           │
  │  • SlowAPI Rate Limiting & Security Headers Middleware      │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 │ SSL Encrypted / Connection Pooling (asyncpg)
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  Database Layer: Neon DB                                    │
  │  • Managed Serverless PostgreSQL 16                         │
  │  • Automated branching & point-in-time recovery             │
  │  • Relational constraints & Alembic schema migrations       │
  └─────────────────────────────────────────────────────────────┘
```

### Architectural Highlights
- **Vercel (Frontend):** Serves the pre-bundled React SPA via an edge network, ensuring fast global delivery, zero server maintenance, and automated preview deployments on every push.
- **Render (Backend):** Hosts the asynchronous FastAPI application in a managed container environment with automatic TLS termination and continuous health monitoring.
- **Neon DB (Database):** Provides serverless PostgreSQL with autoscaling compute and native connection pooling. The backend connects asynchronously via `asyncpg` with SSL enforced (`neon.tech` connection parameters handled natively in application configuration).

🔗 **Live Environment:** [HomeLedger Production Portal](https://household-expense-management-system.vercel.app/login)

---

## 3. Core Engineering & System Design

### 3.1 Integer-Cent Currency Precision
Floating-point numbers (`float`/`double`) introduce rounding inaccuracies when accumulated across recurring billing cycles. HomeLedger eliminates this class of defects by enforcing integer-cent storage across all backend layers, database columns, and validation schemas:
- \$150.50 is represented internally as `15050` cents.
- Presentation formatting (`$150.50` or localized currencies) is deferred strictly to the frontend UI layer via `Intl.NumberFormat`.

### 3.2 Projection-Based Ledger Model
Balances are never stored as static or directly mutable columns (`UPDATE balances SET amount = ...`). Instead, a resident's net balance is calculated as a read-side projection across recorded events within an active billing cycle:
- **Debits:** Sum of assigned expense splits for the resident.
- **Credits:** Sum of verified resident payments.
- **Concessions:** Sum of formally recorded and audited debt waivers.

This guarantees an immutable audit trail: every dollar owed or paid is traceable back to a distinct transaction record.

### 3.3 Deterministic Split Engine
Shared costs rarely divide into round integers. HomeLedger's split engine deterministically distributes remainder cents to guarantee that the sum of split allocations strictly equals the total invoice amount:
- **Equal Split:** Divides integer cents among participants; leftover cents are distributed deterministically across participants.
- **Percentage Split:** Calculates integer shares based on assigned percentages; residual fractions are prioritized to the largest percentage holders.
- **Exact Split:** Validates that explicitly entered amounts match the total down to the cent before persisting.
- **Weighted Split:** Proportional allocation according to arbitrary weights (e.g., room size, residency duration).

### 3.4 Two-Tier Expense Lifecycle
Household bills naturally fall into two categories:
1. **Fixed Recurring:** Contractual monthly obligations (rent, internet) where amount and split ratios are pre-established and instantiated automatically when a cycle opens.
2. **Variable Recurring:** Operational utilities (water, power, gas) where the billing line item is reserved upon cycle creation (`Awaiting Bill`), and dynamically recalculates participant shares once the actual invoice is entered.

Cycles cannot be closed until all pending variable bills are resolved, preventing unallocated liabilities.

### 3.5 Multi-Tenancy & Role-Based Access Control (RBAC)
- Data isolation is enforced at the query level; all entities are bound to a `Household` tenant.
- Role checks are implemented via declarative FastAPI dependency injection:
  - **`ADMIN`:** Manages billing cycles, configures recurring templates, invites members, and approves audited debt waivers.
  - **`MEMBER`:** Views balances, registers one-off expenses, enters utility invoices, and submits payments.

---

## 4. Technical Stack

| Layer | Technology | Purpose & Implementation |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite | Strongly-typed SPA, component architecture, fast build pipeline |
| **Styling & UI** | Tailwind CSS, Lucide Icons | Responsive modern layout, accessible design tokens |
| **Client State** | TanStack Query v5 | Scoped server-cache management, optimistic updates, query invalidation |
| **Backend API** | Python 3.13, FastAPI | Asynchronous REST endpoints, automatic OpenAPI documentation |
| **Validation** | Pydantic v2 | Strict serialization, compile-time and runtime data validation contracts |
| **ORM & Migrations** | SQLAlchemy 2.0 (Async), Alembic | Asynchronous database access (`asyncpg`), versioned schema migrations |
| **Database** | PostgreSQL 16 (Neon DB) / SQLite | Relational integrity, serverless cloud storage, SQLite for local testing |
| **Security & Auth** | Bcrypt, PyJWT, SlowAPI | Cost-factor 12 password hashing, rotating refresh tokens, rate limiting |
| **Code Quality** | SonarCloud, Pytest, ESLint | Automated SAST, coverage tracking, static type checking |
| **DevOps** | Docker, Docker Compose, Nginx | Multi-stage production containerization, local orchestration |

---

## 5. Automated Testing & Code Quality

HomeLedger maintains strict quality gates enforced through continuous integration.

```text
 [ Push / PR to main ]
          │
          ├──> backend-test   : Python 3.13 + Alembic + Pytest (async test suite & coverage.xml)
          ├──> frontend-check : Node 22 + TypeScript (tsc --noEmit) + Vite production build
          ├──> docker-verify  : Multi-container production build validation
          └──> sonarcloud     : Static Application Security Testing (SAST) & Quality Gate verification
```

- **Quality Gate Criteria:**
  - $\ge 80\%$ test coverage on new code.
  - Grade **A** ratings across Security, Reliability, and Maintainability.
  - 0 open vulnerabilities or security hotspots.
- **Interactive Documentation:**
  - Swagger UI: Available locally at `/docs` or via the backend service.
  - ReDoc: Available at `/redoc`.

---

## 6. Local Development & Quick Start

### Prerequisites
- **Python 3.10+** & **Node.js 18+** (or **Docker** with Docker Compose)

### One-Command Setup & Launch (Cross-Platform)
The repository includes automated orchestration scripts that configure virtual environments, install dependencies, run migrations, and launch both servers concurrently:

```bash
# 1. Setup backend virtualenv, install dependencies, and run migrations
python run.py setup

# 2. Start backend (FastAPI :8000) and frontend (Vite :5173) concurrently
python run.py start

# 3. Run automated verification suite (Pytest + Frontend build)
python run.py test
```

*Platform-specific convenience scripts are also provided:*
- **Windows:** Run `.\setup.ps1` and `.\start-dev.ps1` (or double-click `setup.bat` / `start-dev.bat`).
- **Linux / macOS:** Run `./setup.sh` and `./start-dev.sh`.

### Running with Docker Compose
To run the full containerized stack locally with PostgreSQL and Nginx:
```bash
docker compose up --build
```
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 7. Configuration Reference

Key environment variables configured for deployment and local execution:

| Variable | Scope | Description |
|---|---|---|
| `DATABASE_URL` | Backend | Async database URI (`postgresql+asyncpg://...` or `sqlite+aiosqlite:///...`) |
| `SECRET_KEY` | Backend | Cryptographic secret for signing JWT access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | Lifetime of access tokens (default: `30` min) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Backend | Lifetime of rotating refresh tokens (default: `30` days) |
| `BACKEND_CORS_ORIGINS` | Backend | JSON array or comma-separated list of allowed origins |
| `VITE_API_URL` | Frontend | Base URL of the backend API (empty string defaults to relative proxy) |

---

## 8. License

This project is released under the **Non-Commercial Software License and Usage Agreement**.
- **Allowed:** Personal household management, academic review, code auditing, and portfolio demonstration.
- **Restricted:** Commercial distribution, resale, or operating as a commercial Software-as-a-Service (SaaS) without express written consent.
- For complete terms, see [`LICENSE.md`](./LICENSE.md).