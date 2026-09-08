# HomeLedger — Shared Household Expense Management System

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=coverage)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=MatheusPMello_household-expense-management-system&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=MatheusPMello_household-expense-management-system)

HomeLedger is a multi-tenant web application designed for managing, allocating, and auditing shared household expenses. Built with a focus on mathematical precision, security, and ledger-based accounting, the system handles two-tier recurring expense templates (both fixed contracts and variable utility/condo bills), ad-hoc one-off costs, penny-perfect split algorithms, partial or full settlements, and audited debt forgiveness.

---

## 1. Executive Summary & Problem Context

Shared living arrangements and multi-resident households frequently face accounting friction:
- **Floating-point rounding anomalies:** Traditional expense tracking tools using floating-point numbers often accumulate fractional-cent discrepancies over recurring cycles.
- **Direct balance mutations:** Directly modifying resident balances (`SET balance = X`) obscures the audit trail and makes financial reconciliation difficult.
- **Unclear debt forgiveness:** Forgiven shortfalls or informal chore offsets are often deleted or untracked, distorting active monthly operations and erasing historical records.
- **Cross-household isolation:** Shared setups require rigorous data isolation between households and distinct permission tiers for administrators versus standard residents.

HomeLedger addresses these issues through strict integer-cent storage, a projection-based ledger model, deterministic penny-perfect split algorithms, two-tier recurrence templates with dynamic monthly recalculation, and an immutable audit trail for concessions.

---

## 2. Technical Stack

| Layer | Technologies | Key Capabilities |
|---|---|---|
| **Backend** | Python 3.13, FastAPI, Pydantic v2 | High-performance asynchronous REST API, strict request/response data contracts, declarative validation |
| **Data & ORM** | PostgreSQL 16 / SQLite, SQLAlchemy 2.0 (Async), Alembic | Asynchronous I/O via `asyncpg`/`aiosqlite`, relational integrity constraints, automated migration management |
| **Security & Auth** | Bcrypt, PyJWT, SlowAPI | High-entropy password hashing (cost factor 12), short-lived access tokens, database-persisted rotating refresh tokens, endpoint rate limiting, secure HTTP headers |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Type-safe single-page application (SPA), responsive interface, accessible components, real-time client-side preview calculations |
| **State Management** | TanStack Query v5 (React Query) | Granular client-side caching keyed by billing cycle and household scopes, automatic cache invalidation |
| **Quality & Security** | SonarCloud, Pytest-Cov, ESLint/TypeScript | Automated SAST (Static Application Security Testing), code smell detection, test coverage tracking, Quality Gate enforcement |
| **Infrastructure** | Docker, Docker Compose, Nginx | Multi-stage production container builds, reverse proxy routing, automated database health checks |

---

## 3. Core Architectural & Accounting Principles

### 3.1 Integer Precision (Cents)
No monetary values are stored or calculated as floating-point numbers (`float` or `double`). All financial attributes in the database and calculation engines are stored as integers representing cents:
$$\$150.50 \longrightarrow 15050 \text{ cents}$$
Currency formatting (`$150.50`) is exclusively applied at the presentation layer using the browser's native `Intl.NumberFormat`.

### 3.2 Ledger-Based Balance Projection
A resident's balance is never updated as a static field. Instead, active balances are computed dynamically as a projection across recorded financial events:

$$\text{Current Balance } (S_p) = D_p - (P_p + W_p)$$

Where:
- $D_p$: Sum of all assigned expense splits for person $p$ within the active billing cycle.
- $P_p$: Sum of all payments recorded by person $p$ within the active billing cycle.
- $W_p$: Sum of all debt waivers granted to person $p$ within the active billing cycle.

**Evaluation:**
- $S_p = 0$: Cycle is fully settled.
- $S_p > 0$: Pending liability owed by the resident.
- $S_p < 0$: Credit balance (overpayment).

### 3.3 Penny-Perfect Split Engine
The application implements four deterministic split strategies that guarantee zero lost cents:

1. **Equal Split (`EQUAL`):**
   $$Q = \lfloor \text{total\_cents} / N \rfloor, \quad R = \text{total\_cents} \pmod N$$
   The first $R$ participants are allocated $Q + 1$ cents; the remaining $N - R$ participants receive $Q$ cents. The sum of allocations strictly matches `total_cents`.
2. **Percentage Split (`PERCENTAGE`):**
   Each participant receives $\lfloor \text{total\_cents} \times \frac{p_i}{100} \rfloor$. Residual cents resulting from fractional rounding are distributed to the participants with the largest share percentages.
3. **Exact Split (`EXACT`):**
   Explicit values are checked at the schema level: $\sum \text{assigned\_amount\_cents} \equiv \text{total\_amount\_cents}$. Any divergence returns HTTP 422.
4. **Weighted Split (`WEIGHTED`):**
   Allocations are computed proportionally based on input weights, with residual cents assigned to the highest-weight participants.

### 3.4 Multi-Tenant Household Scope & RBAC
- Each resident entity (`Person`) and billing cycle is strictly associated with a `Household`.
- All requests are verified through FastAPI dependencies checking membership and permissions:
  - **`ADMIN`:** Can create and close billing cycles, create recurring templates, grant debt waivers, and invite new members.
  - **`MEMBER`:** Can review balances, submit variable expenses, and register personal payments.

---

## 4. System Architecture

```text
       [ React 18 + Vite + TypeScript (SPA) ]
                         │
                         │ HTTP REST (JSON / JWT Bearer)
                         ▼
       [ FastAPI Application Layer ]
         ├── Security Headers & CORS Middleware
         ├── SlowAPI Rate Limiting (Brute-force protection)
         ├── Auth & Household Scope Dependencies
         │
         ├── Business Logic & Calculation Engines
         │     ├── Split Engine (Equal, Percentage, Exact, Weighted)
         │     ├── Cycle Lifecycle Service (Auto-instantiation & Locking)
         │     └── Balance & Reporting Projections Service
         │
         └── SQLAlchemy 2.0 Async Session Layer
                         │
                         │ asyncpg / aiosqlite
                         ▼
       [ Relational Database (PostgreSQL 16 / SQLite) ]
         ├── users & refresh_tokens
         ├── households & household_members (RBAC)
         ├── persons (managed residents)
         ├── fixed_expense_templates (recurring templates: FIXED & VARIABLE with split configs)
         ├── billing_cycles
         ├── expenses & expense_splits (with lifecycle status: PENDING_VALUE, READY, SETTLED)
         ├── payments
         └── debt_waivers (audited log)
```

---

## 5. Configuration & Setup

### 5.1 Prerequisites
- **For Containerized Execution:** Docker and Docker Compose.
- **For Local Native Execution:** Python 3.10+ and Node.js 18+.

---

### 5.2 Fast Automated Setup & Launch (One-Command)

HomeLedger includes cross-platform scripts that automatically configure the virtual environment, install backend & frontend dependencies, run Alembic migrations, and start both servers concurrently.

#### Universal (Cross-Platform via Python)
```bash
# 1. Automatic configuration (venv, pip, migrations, npm)
python run.py setup

# 2. Start both backend and frontend development servers
python run.py start

# 3. Run full automated verification (pytest + frontend build)
python run.py test
```

#### Windows (PowerShell or Double-Click Batch)
- **PowerShell:** Run `.\setup.ps1` to configure, then `.\start-dev.ps1` to launch.
- **Double-click:** You can also simply double-click `setup.bat` followed by `start-dev.bat`.

#### Linux / macOS (Bash)
```bash
chmod +x setup.sh start-dev.sh
./setup.sh        # Fast setup & migrations
./start-dev.sh     # Launch backend & frontend
```

---

### 5.3 Option A: Running with Docker Compose

To run the complete production stack (PostgreSQL 16, FastAPI backend, and React/Nginx frontend) in isolated containers:

```bash
docker compose up --build
```
- **Frontend Application:** [http://localhost:3000](http://localhost:3000)
- **Interactive Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative API Docs (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 5.4 Option B: Manual Step-by-Step Setup

#### 1. Backend Setup
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The backend server runs on `http://localhost:8000` using SQLite (`homeledger.db`) by default. To connect to an external PostgreSQL instance, set `DATABASE_URL`:
```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/homeledger"
```

#### 2. Frontend Setup
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
The frontend development server runs on `http://localhost:5173`.

---

### 5.4 Environment Variables Reference

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./homeledger.db` | Async database connection URI (`postgresql+asyncpg://...` or `sqlite+aiosqlite://...`) |
| `SECRET_KEY` | *(Set in config)* | High-entropy secret key used for signing JWT tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Lifespan of the access token in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Lifespan of rotating refresh tokens in days |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:3000", "http://localhost:5173"]` | JSON list of allowed origins for CORS headers |

---

## 6. Functional Walkthrough & User Guide

### 6.1 Authentication & Household Onboarding
1. **User Registration:** Navigate to `/register`. Registering a new account automatically creates a primary household entity with the user assigned as `ADMIN`, and registers an initial resident profile.
2. **Multi-Household Switching:** Users can belong to multiple households (e.g., apartment, holiday house). The dropdown in the navigation header allows switching between active contexts.

### 6.2 Managing Residents and Recurring Expense Templates
1. **Resident Directory:** Navigate to **Settings**. The administrator can register managed residents (`Person` entities). Residents can exist as standalone profiles (e.g., dependents, roommates without accounts) or be linked to registered user accounts.
2. **Recurring Expense Templates (Fixed & Variable):** Under **Settings**, configure recurring monthly obligations:
   - **Fixed Recurring:** Set a contract amount (e.g., Rent, Fiber Internet) and due day (1–31). Generates ready bills with predetermined splits on each new cycle.
   - **Variable Recurring:** For costs where the amount changes every month (e.g., Electricity, Water, HOA/Condo fees), set a due day and an optional estimated baseline. Instantiates monthly drafts awaiting the real invoice amount.
3. **Member Invitations:** Household administrators can invite other registered users by email and assign their role (`ADMIN` or `MEMBER`).

### 6.3 Billing Cycles & Expense Splitting
1. **Initializing a Billing Cycle:** On the **Current Cycle** dashboard, select **New Cycle**. Creating a cycle automatically instantiates active recurring templates:
   - **Fixed Expenses:** Appear pre-filled with the contract amount, marked with `READY` status, and splits immediately allocated without penny loss.
   - **Variable Expenses:** Appear with an amber `Awaiting Bill` badge (`PENDING_VALUE` status, $0.00), reserving the expense item without prematurely assigning unbilled liabilities to residents.
2. **Registering Expenses (Modal Workflow):** Navigate to **Expenses** and click **+ Add Expense**. Select the expense nature:
   - **One-off (Single):** Single expense with immediate due date and amount for the active cycle only.
   - **Fixed Recurring:** Contract amount and recurring due day; creates an active template repeating automatically every cycle.
   - **Variable Recurring:** Recurring due day, optional estimated baseline, and split rules; creates an active template and a pending draft in the active cycle.
3. **Confirming Variable Invoices & Dynamic Split Recalculation:** When the monthly utility or condo invoice arrives, click **Enter Bill** on the table row (or open the micro-modal):
   - Enter the actual invoice amount.
   - Optionally toggle *"Update recurring template default estimated amount for future months"* if the contractual baseline has changed.
   - Click **Confirm & Recalculate Split**: The split engine automatically distributes the bill across participating residents using the assigned formula (`EQUAL`, `PERCENTAGE`, `WEIGHTED`) down to the exact integer cent, transitions the expense status to `READY`, and updates resident balances without manual arithmetic.
4. **Interactive Split Engine:** Choose the calculation method (`EQUAL`, `PERCENTAGE`, `EXACT`, `WEIGHTED`) and select participants. A real-time split preview displays the allocation breakdown down to the exact cent before submission.
5. **Expense Settlement Status:** Expenses support a `Paid` toggle, enabling the household to track whether a utility bill or invoice has been settled externally independently of internal resident collections.

### 6.4 Settlements & Audited Debt Waivers
1. **Recording Resident Payments:** Click **+ Record Payment** on any resident card. Enter the amount settled and optional reference notes. The resident's remaining balance updates immediately.
2. **Granting Audited Debt Waivers:** When a resident's balance is forgiven (e.g., labor offset, mutual agreement), an administrator can click **Waive Amount**. Entering an audited reason is mandatory. The amount is credited against the current operational cycle while preserving an entry in the historical ledger.

### 6.5 Consolidated Reporting & Cycle Closure
1. **Current Cycle Dashboard:** Provides an operational view of total budget, settled expenses, collections received, and individual resident balances (`Settled`, `Owed`, or `Credit`).
2. **General Balance & Historical Audit:**
   - **Debt Waiver Ledger:** Comprehensive table displaying all historical waivers across cycles, including date, participant, amount, and audited reason.
   - **Resident Compliance Rate:** Tracks long-term contribution compliance:
     $$\text{Compliance Rate} = \frac{\sum P_p}{\sum D_p} \times 100\%$$
   - **Cost Trajectory:** Visual representation comparing monthly fixed vs. variable spending trends over time.
3. **Closing a Cycle:** Once a billing period concludes, administrators can click **Close Cycle**. This action locks the cycle, preventing further expense creation, payments, or modifications unless reopened. The system enforces a strict accounting safety check: cycles cannot be closed while any recurring expenses remain in `PENDING_VALUE` (`Awaiting Bill`), ensuring all household liabilities are accounted for.

---

## 7. Testing & Verification

The test suite covers algorithmic accuracy, permission boundaries, and ledger integrity.

### 7.1 Backend Automated Tests (Pytest)
Run the automated test suite from the `backend/` directory:

```bash
cd backend
pytest -v
```

**Test Coverage Areas:**
- `test_split_engine.py`: Equal splits with prime cents remainders, percentage rounding residuals, exact sum validation, and weighted splits.
- `test_auth_and_rbac.py`: Registration, authentication, token rotation, revoked token rejection, and cross-household data isolation.
- `test_cycles_and_ledger.py`: Full cycle lifecycle, template auto-instantiation (fixed and variable), dynamic split recalculation, waiver ledger audit trail, and cycle lock safety.

### 7.2 Frontend Type Checking & Build Verification
Verify TypeScript compilation and Vite production bundling from the `frontend/` directory:

```bash
cd frontend
npm run build
```

### 7.3 Continuous Integration (GitHub Actions CI Gate)

A dedicated GitHub Actions workflow is located at [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) that triggers automatically on every:
- **Pull Request** targeting `main`
- **Push / Merge** to `main`
- **Manual Dispatch** via the GitHub Actions UI

**Pipeline Stages:**
1. **`backend-test`:** Sets up Python 3.13, applies Alembic migrations, and runs the Pytest suite with code coverage tracking (`backend/coverage.xml`).
2. **`frontend-check`:** Sets up Node.js 22, performs TypeScript strict type checking (`tsc --noEmit`), and executes the production Vite build.
3. **`docker-verify`:** Builds the multi-container production Docker Compose stack (`db`, `backend`, `frontend`) to ensure deployment readiness.
4. **`sonarcloud-scan`:** Executes SonarCloud static analysis (Python & TypeScript), imports the Pytest coverage XML report, and verifies the automated Quality Gate.
5. **`quality-gate`:** Aggregates status across all preceding jobs. If any test, build, or security gate fails, the pipeline halts immediately, preventing pull request merges or broken deployments.

---

### 7.4 Code Quality & Static Analysis (SonarCloud)

HomeLedger integrates **SonarCloud** in its continuous integration pipeline to ensure architectural hygiene, security compliance (OWASP Top 10), and test coverage tracking across both the Python FastAPI backend and the React TypeScript frontend.

#### Configuration Structure
- **Root Configuration:** [`sonar-project.properties`](./sonar-project.properties) configures project keys, source roots (`backend/app`, `frontend/src`), test suites (`backend/tests`), and report bindings.
- **Automated Coverage Ingestion:** Ingests `backend/coverage.xml` generated by `pytest-cov` during the `backend-test` stage.
- **TypeScript AST Analysis:** Scans client-side logic mapped through [`frontend/tsconfig.json`](./frontend/tsconfig.json) for code smells, type soundness, and duplicated components.
- **Sanitized Exclusions:** Excludes third-party dependencies (`node_modules`, `venv`), compiled output (`dist`), database binaries (`*.db`), test caches, and database migration histories.

#### GitHub Repository Secrets Setup
To link your repository to SonarCloud:
1. Log in to [SonarCloud](https://sonarcloud.io) using your GitHub account and import your repository.
2. In SonarCloud, disable **Automatic Analysis** under **Project Settings > Analysis Method** and select **With GitHub Actions**.
3. Generate an access token in SonarCloud (**My Account > Security > Generate Token**).
4. Add the token to GitHub under **Settings > Secrets and variables > Actions** as `SONAR_TOKEN`.

#### Enforced Quality Gate Criteria
Commits and Pull Requests must satisfy the following Quality Gate conditions:
- **Test Coverage:** $\ge 80\%$ on newly introduced code.
- **Security Rating:** Grade **A** (0 open vulnerabilities or security hotspots).
- **Reliability Rating:** Grade **A** (0 unresolved bugs).
- **Maintainability Rating:** Grade **A** (technical debt ratio $< 5\%$).
- **Duplicated Code:** $< 3\%$ duplication across all source files.

---

## 8. REST API Reference

All protected endpoints require the `Authorization: Bearer <access_token>` header. Household-scoped operations accept the `X-Household-Id` header or `household_id` query parameter.

| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Create user account and initialize personal household |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and issue access + rotating refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Public | Rotate refresh token and issue new token pair |
| `POST` | `/api/v1/auth/logout` | Authenticated | Revoke refresh token |
| `GET` | `/api/v1/auth/me` | Authenticated | Fetch current user profile and household memberships |
| `POST` | `/api/v1/households` | Authenticated | Create a new household (creator assigned as `ADMIN`) |
| `GET` | `/api/v1/households/{id}/members` | Member | List members and assigned roles |
| `POST` | `/api/v1/households/{id}/members` | Admin | Invite/add a registered user to the household |
| `GET` | `/api/v1/households/{id}/persons` | Member | List managed residents in the household |
| `POST` | `/api/v1/households/{id}/persons` | Member | Register a resident in the household |
| `GET` | `/api/v1/fixed-templates` | Member | List recurring expense templates (fixed contract amounts or variable bills) |
| `POST` | `/api/v1/fixed-templates` | Admin | Create recurring expense template (`FIXED` or `VARIABLE`) with split config |
| `PUT` | `/api/v1/fixed-templates/{id}` | Admin | Update recurring template rules, amounts, or active status |
| `DELETE` | `/api/v1/fixed-templates/{id}` | Admin | Delete recurring expense template |
| `GET` | `/api/v1/cycles` | Member | List billing cycles with year/month filtering |
| `POST` | `/api/v1/cycles` | Admin | Initialize cycle and instantiate recurring templates |
| `POST` | `/api/v1/cycles/{id}/close` | Admin | Close and lock billing cycle (requires all pending bills to be resolved) |
| `POST` | `/api/v1/cycles/{id}/reopen` | Admin | Reopen a closed billing cycle |
| `POST` | `/api/v1/expenses` | Member | Create expense (single or recurring) with penny-perfect split calculation |
| `PUT` | `/api/v1/expenses/{id}` | Member | Update expense details and recalculate splits |
| `PATCH`| `/api/v1/expenses/{id}/amount` | Member | Set actual invoice amount on recurring bill and recalculate splits |
| `PATCH`| `/api/v1/expenses/{id}/payment-status`| Member | Toggle external payment settlement flag |
| `DELETE`| `/api/v1/expenses/{id}` | Member | Delete expense from an open billing cycle |
| `POST` | `/api/v1/settlements/payments` | Member | Record resident contribution payment |
| `POST` | `/api/v1/settlements/waivers` | Admin | Record audited debt waiver with mandatory reason |
| `GET` | `/api/v1/reports/current-cycle` | Member | Generate operational balance sheet for a cycle |
| `GET` | `/api/v1/reports/general-balance` | Member | Generate historical consolidation and waiver audit report |

---

## 9. License & Commercial Restrictions

This project is licensed under the **Non-Commercial Software License and Usage Agreement**.

- **Personal & Educational Use:** Free for personal household expense management, academic review, code auditing, and non-commercial portfolio demonstration.
- **Commercial Restriction:** Commercialization, resale, sublicensing, integration into commercial software products, or operating as a paid Software-as-a-Service (SaaS) is strictly prohibited without prior written permission from the Creator.
- For complete terms, see [`LICENSE.md`](./LICENSE.md). For commercial licensing inquiries, contact the creator via the project repository.