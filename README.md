# Student Data Verification Portal

A web-based portal that allows administrators to upload student records (via Excel) and collect missing information directly from students. Fields marked with `[COLLECT]` in the spreadsheet become editable input fields for each student, while all other data remains read-only.

> **Current status — Step 1: Development Foundation**
>
> Only the project skeleton and frontend ↔ backend connectivity have been implemented. Features such as Excel upload, student forms, authentication, and database integration will be added in later phases.

---

## Technology Stack

| Layer    | Technology                  |
| -------- | --------------------------- |
| Frontend | React · TypeScript · Vite   |
| Backend  | Python 3.13 · FastAPI · Uvicorn |
| Database | PostgreSQL *(planned — not yet implemented)* |

---

## Project Structure

```
student-data-portal/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Environment-based settings
│   │   ├── main.py            # FastAPI application entry point
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py      # GET /api/health
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
├── .gitignore
└── README.md
```

---

## Prerequisites

| Software   | Version  |
| ---------- | -------- |
| Python     | 3.13+    |
| Node.js    | 18+      |
| npm        | 9+       |

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd student-data-portal
```

### 2. Backend setup

```bash
cd backend

# Create the Python 3.13 virtual environment
python3.13 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Copy and customise environment variables
cp .env.example .env
```

### 3. Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# (Optional) Copy and customise environment variables
cp .env.example .env
```

---

## Running the Application

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

## Verifying Frontend → Backend Communication

1. Start both the backend and frontend servers as described above.
2. Open **http://localhost:5173** in your browser.
3. You should see:
   - The title **"Student Data Verification Portal"**
   - A status card showing **Backend Status: Connected** (with a green indicator).
4. Alternatively, call the health endpoint directly:

```bash
curl http://localhost:8000/api/health
# Expected response: {"status":"ok"}
```

If the backend is not running, the status card will show **Backend Status: Disconnected** (with a red indicator).

---

## Environment Variables

### Backend (`backend/.env`)

| Variable       | Default                  | Description                              |
| -------------- | ------------------------ | ---------------------------------------- |
| `CORS_ORIGINS` | `http://localhost:5173`  | Comma-separated list of allowed origins  |
| `HOST`         | `0.0.0.0`               | Server bind address                      |
| `PORT`         | `8000`                   | Server port                              |

### Frontend (`frontend/.env`)

| Variable             | Default                  | Description                     |
| -------------------- | ------------------------ | ------------------------------- |
| `VITE_API_BASE_URL`  | `http://localhost:8000`  | Backend API base URL            |

---

## License

This project is private and not yet licensed for distribution.
