# Student Data Verification Portal

A web-based portal that allows administrators to upload student records (via Excel) and collect missing information directly from students. Fields marked with `[COLLECT]` in the spreadsheet become editable input fields for each student, while all other data remains read-only.

> **Current status — Step 2: PostgreSQL Database Foundation**
>
> The project skeleton, frontend ↔ backend connectivity, and PostgreSQL database foundation are implemented. Features such as Excel upload, student forms, authentication, and application schema will be added in later phases.

---

## Technology Stack

| Layer    | Technology                                  |
| -------- | ------------------------------------------- |
| Frontend | React · TypeScript · Vite                   |
| Backend  | Python 3.13 · FastAPI · Uvicorn             |
| Database | PostgreSQL 17 · SQLAlchemy 2.x · Alembic    |
| Infra    | Docker Compose (PostgreSQL only)            |

---

## Project Structure

```
student-data-portal/
├── backend/
│   ├── alembic/
│   │   ├── versions/          # Migration scripts
│   │   └── env.py             # Alembic environment (reads app settings)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Environment-based settings
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   └── session.py     # SQLAlchemy engine, session, Base, get_db
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── system_metadata.py  # Initial proof-of-concept model
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py      # GET /api/health (app + DB check)
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_database.py   # Database foundation tests
│   ├── alembic.ini
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── App.css
│   │   ├── App.tsx            # Main React component
│   │   ├── config.ts          # Frontend configuration
│   │   ├── index.css          # Global styles / design system
│   │   └── main.tsx           # React entry point
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── docker-compose.yml         # PostgreSQL service
├── .env.example               # Docker Compose env vars
├── .gitignore
└── README.md
```

---

## Prerequisites

| Software        | Version  |
| --------------- | -------- |
| Python          | 3.13+    |
| Node.js         | 18+      |
| npm             | 9+       |
| Docker Desktop  | Latest   |

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd student-data-portal
```

### 2. PostgreSQL setup

Ensure Docker Desktop is running, then start PostgreSQL:

```bash
docker compose up -d
```

Verify the container is healthy:

```bash
docker compose ps
```

You should see `sdvp-postgres` with status `Up ... (healthy)`.

### 3. Backend setup

```bash
cd backend

# Create the Python 3.13 virtual environment
python3.13 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env

# Apply database migrations
alembic upgrade head
```

### 4. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# (Optional) Copy and customise environment variables
cp .env.example .env
```

---

## Running the Application

### Start PostgreSQL (from project root)

```bash
docker compose up -d
```

### Start the backend (from `backend/`)

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **http://localhost:8000**.

### Start the frontend (from `frontend/`)

```bash
npm run dev
```

The development server will start at **http://localhost:5173** (default Vite port).

---

## Verifying the Application

### Health endpoint

```bash
curl http://localhost:8000/api/health
```

Expected response when PostgreSQL is running:

```json
{"status": "ok", "database": "connected"}
```

When PostgreSQL is stopped, the endpoint returns HTTP 503:

```json
{"status": "degraded", "database": "disconnected"}
```

### Frontend

Open **http://localhost:5173** in your browser. You should see:

- The title **"Student Data Verification Portal"**
- A status card showing **Backend Status: Connected** (with a green indicator)

---

## Database Migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema management.

### Apply all migrations

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Create a new migration after model changes

```bash
alembic revision --autogenerate -m "description of changes"
```

### View migration history

```bash
alembic history
```

### Downgrade one revision

```bash
alembic downgrade -1
```

> **Important:** Never modify the database schema outside of Alembic migrations. Always create a migration for schema changes.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pip install pytest httpx    # test dependencies (one-time)
python -m pytest tests/ -v
```

Tests require PostgreSQL to be running (`docker compose up -d`).

---

## Managing PostgreSQL

### Stop PostgreSQL (preserves data)

```bash
docker compose down
```

The named volume `sdvp_pgdata` preserves all database data across container restarts.

### Completely remove the development database

To destroy all data and start fresh:

```bash
docker compose down -v
```

This removes both the container and the named volume. After this, you will need to re-run `alembic upgrade head` to recreate the schema.

---

## Environment Variables

### Project root (`.env`) — Docker Compose

| Variable            | Default              | Description              |
| ------------------- | -------------------- | ------------------------ |
| `POSTGRES_DB`       | `sdvp`               | Database name            |
| `POSTGRES_USER`     | `sdvp_user`          | Database user            |
| `POSTGRES_PASSWORD` | `sdvp_dev_password`  | Database password        |
| `POSTGRES_PORT`     | `5432`               | Host port for PostgreSQL |

### Backend (`backend/.env`)

| Variable       | Default                                                             | Description                              |
| -------------- | ------------------------------------------------------------------- | ---------------------------------------- |
| `CORS_ORIGINS` | `http://localhost:5173`                                             | Comma-separated list of allowed origins  |
| `HOST`         | `0.0.0.0`                                                          | Server bind address                      |
| `PORT`         | `8000`                                                              | Server port                              |
| `DATABASE_URL` | `postgresql+psycopg://sdvp_user:sdvp_dev_password@localhost:5432/sdvp` | PostgreSQL connection string          |

### Frontend (`frontend/.env`)

| Variable             | Default                  | Description                     |
| -------------------- | ------------------------ | ------------------------------- |
| `VITE_API_BASE_URL`  | `http://localhost:8000`  | Backend API base URL            |

---

## License

This project is private and not yet licensed for distribution.
# Student-Information-Portal
