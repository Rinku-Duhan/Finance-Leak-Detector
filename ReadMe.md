# 💸 Finance Leak Detector

A production-style transaction intelligence platform that analyzes bank/UPI statements to detect spending anomalies — duplicate charges, price creep, dormant subscriptions, and category drift — using **deterministic, evidence-based detection** enhanced with narrow, well-justified LLM capabilities.

![CI](https://github.com/Rinku-Duhan/finance-leak-detector/actions/workflows/ci.yml/badge.svg)

🔗 **Live demo**: [[https://finance-leak-frontend.onrender.com](https://finance-leak-detector-1.onrender.com/)](https://finance-leak-detector-nel1.onrender.com)
   (Free tier — first load may take 30-60s to wake up)

## Why this project

This project exists to demonstrate production software engineering — SQL, auth, cloud deployment, CI/CD, and testing discipline — on top of already-proven ML/data skills. The anomaly detection itself is deliberately **100% deterministic and rule-based**, not a black-box model: every flagged leak comes with explicit evidence (amounts, dates, percentage changes) and a severity level derived from documented thresholds. No confidence scores — a rule-based detector can't produce a mathematically defensible probability, so evidence + severity replace that honestly instead.

## Architecture

<img src="docs\detailed_system_architecture.svg" alt="Architecture diagram" width="700"/>

- **Backend**: FastAPI + SQLAlchemy + Alembic, deployed on Render
- **Database**: PostgreSQL, hosted on Neon (serverless, scales to zero)
- **Auth**: Hand-built JWT (access + refresh token pair), bcrypt password hashing
- **Frontend**: Streamlit (chosen deliberately over React — see *Design Decisions* below)
- **LLM**: Groq (`openai/gpt-oss-20b`) — used only for merchant categorization fallback and monthly narrative text, both cached/on-demand to control cost
- **CI/CD**: GitHub Actions runs the full test suite + validates both Docker images build, on every push
- **Containerization**: Docker + Docker Compose for local dev parity; Render builds directly from the Dockerfile for deployment

## The four detectors

| Detector | What it catches | Thresholds |
|---|---|---|
| **Duplicate Charge** | Same merchant + exact same amount, close together in time | ≤6h → HIGH, 6–24h → MEDIUM, 24–72h → LOW |
| **Price Creep** | A subscription/membership's price rises vs. its own recent baseline | ≥25% increase → HIGH, ≥10% → MEDIUM (Subscriptions/Fitness categories only — discretionary spend naturally varies too much per visit to apply this reliably) |
| **Dormant Subscription** | A subscription charged consistently for many consecutive months | ≥10 months → HIGH, ≥6 → MEDIUM, ≥3 → LOW |
| **Category Drift** | Sustained rise in a spending category vs. historical baseline, with a statistical-significance guard against normal month-to-month noise | ≥50% increase (and ≥1.5σ above baseline) → HIGH, ≥25% → MEDIUM |

### Measured accuracy (against synthetic ground truth)

Evaluated against 8 synthetic users (12 months each, ~280–300 transactions/user) with 18 deliberately injected anomalies, including combined multi-anomaly cases:

- **Recall: 18/18 (100%)** — every injected anomaly was caught with the correct severity
- **Precision: 18/20 (90%)** — 2 honest false positives, both traced to natural statistical noise in low-sample-size spending categories (documented in `category_drift.py`)

This is checked automatically on every push via the `pytest` suite (`backend/tests/`) — not a one-time manual claim.

## Setup

### Prerequisites
- Python 3.12+
- A [Neon](https://neon.tech) Postgres database (free tier)
- A [Groq](https://console.groq.com) API key (free tier)

### 1. Clone and set up the environment
```bash
git clone https://github.com/Rinku-Duhan/finance-leak-detector.git
cd finance-leak-detector
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 2. Configure environment variables
Create a `.env` file in the project root:
```
DATABASE_URL=postgresql://...your-neon-connection-string...
JWT_SECRET_KEY=...generate with: python -c "import secrets; print(secrets.token_hex(32))"...
GROQ_API_KEY=...your-groq-key...
```

### 3. Run database migrations
```bash
cd backend
alembic upgrade head
```

### 4. Run the app (two terminals)
```bash
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
streamlit run app.py
```
Backend API docs: `http://127.0.0.1:8000/docs`
Frontend: `http://localhost:8501`

### 5. Generate demo data (optional)
```bash
cd backend/app/data_gen
python generate_data.py
```
Produces 8 synthetic users' worth of transaction CSVs plus a `ground_truth.json` answer key, for testing/demo purposes.

## Testing
```bash
cd backend
pytest tests/ -v
```
44 tests covering the parser, normalizer, rule-based categorizer, and all 4 detectors — run automatically on every push via GitHub Actions.

## Docker
```bash
docker compose up --build
```
Builds and runs both the backend and frontend as containers.

## API overview

```
POST /auth/signup                    → create account, returns token pair
POST /auth/login                     → returns token pair
POST /auth/refresh                   → rotate access + refresh tokens

POST /transactions/upload            → parse, normalize, categorize, detect, store
GET  /transactions/                  → paginated, filterable by upload/category/month

GET  /uploads/                       → list of past uploads (analysis history)
GET  /dashboard/summary?upload_id    → totals, category breakdown
GET  /dashboard/anomalies?upload_id  → detected leaks: type, reason, evidence, severity
GET  /dashboard/narrative?upload_id  → LLM-generated plain-language summary

GET  /categories/                    → list of categories for filter UI
```

Full interactive docs available at `/docs` once the backend is running.

## Database schema

```
users            → id, email, hashed_password, created_at
uploads          → id, user_id, filename, uploaded_at, status
transactions     → id, user_id, upload_id, date, merchant, normalized_merchant,
                    amount, category, category_source
merchant_category→ normalized_merchant, category   (cache — avoids repeat LLM calls)
categories       → id, name
detected_anomalies → id, user_id, upload_id, transaction_id (nullable),
                      type, reason, evidence (JSONB), severity, detected_at
```

Uploads are immutable and never overwritten — every upload is preserved as distinct analysis history, queryable independently.

## Design decisions worth knowing

- **Refresh tokens are stateless JWTs, not DB-tracked**: There's no `refresh_tokens` table, so an individual refresh token can't be server-side revoked before it expires. A production system would add token tracking for that.
- **Dormant subscription detection is a proxy, not proof**: with transaction data alone, there's no way to know a subscription is genuinely unused — only that it's been charged consistently. Findings are framed as "worth reviewing," not "confirmed unused."
- **UUIDs over auto-increment IDs**: standard practice for anything user-facing — sequential integer IDs leak information (e.g. how many users exist) and are unsafe to expose in API responses/URLs.

## Skills demonstrated

**Backend**: FastAPI, REST API design, SQLAlchemy ORM, Alembic migrations, JWT auth, file upload handling
**Database**: PostgreSQL, relational schema design, Postgres-native types (JSONB, ENUM)
**Data engineering**: CSV ingestion across varying bank export formats, merchant normalization, rule-based feature engineering, statistical anomaly detection
**AI (narrow, justified)**: LLM integration with cost-aware caching, prompt engineering
**Software engineering**: modular detector architecture, comprehensive automated testing, evidence-based (non-black-box) design
**DevOps**: Docker, Docker Compose, GitHub Actions CI/CD
**Cloud**: Render (app hosting), Neon (serverless Postgres) — documented honestly as free-tier PaaS

## Project structure

```
finance-leak-detector/
├── backend/
│   ├── app/
│   │   ├── data_gen/          # Synthetic data generator
│   │   ├── detectors/         # 4 anomaly detectors
│   │   ├── routers/           # FastAPI route handlers
│   │   ├── database.py
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── security.py        # JWT + password hashing
│   │   ├── dependencies.py    # Auth dependencies
│   │   ├── pipeline.py        # Upload orchestration
│   │   ├── parser.py
│   │   ├── normalizer.py
│   │   ├── categorizer.py
│   │   ├── categorizer_rules.py
│   │   ├── narrative.py
│   │   └── main.py
│   ├── alembic/                # DB migrations
│   ├── tests/                  # PyTest suite (44 tests)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/                  # Streamlit multi-page app
│   ├── api_client.py
│   ├── app.py                  # Login/signup entry point
│   ├── requirements.txt
│   └── Dockerfile
├── .github/workflows/ci.yml    # CI: tests + Docker build check
├── docker-compose.yml
└── README.md
```

## Screenshots
<img src="docs\signup.png" alt="Singup Page" width="700"/>
<img src="docs\upload-the-file.png" alt="Upload the file" width="700"/>
<img src="docs\Full dashboard.png" alt="Dashboard" width="700"/># Finance-Leak-Detector
