
# Multi-Source Scraper & Aggregator



## Overview

This service lets authenticated users submit scraping jobs against multiple data sources (Books, Quotes, Wikipedia, Yahoo Finance, Y Combinator) and retrieve results in real time. Jobs are executed asynchronously via Celery workers and tracked in Redis, while results and logs are persisted in MongoDB.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI |
| Database | MongoDB |
| Cache / Job Tracking | Redis |
| Task Queue | Celery + Flower UI |
| Scraping | httpx + BeautifulSoup4 (static), Selenium |
| Auth | JWT (PyJWT) with access & refresh tokens |
| Containerisation | Docker + Docker Compose |

---

## Features

**Multi-source scraping** — books.toscrape.com, quotes.toscrape.com, Wikipedia, Yahoo Finance (via Selenium), Y Combinator
**Async job queue** — each scrape runs as a background Celery task; results stream into Redis in real time
**Job lifecycle management** — create, monitor, list, cancel, and retrieve results for any scrape job
**JWT authentication** — access tokens and refresh tokens
**Role-based access** — regular users and admins; admin-only routes for listing all jobs.
**Redis-backed account lockout** — tracks failed login attempts; locks account for 10 minutes after 5 consecutive failures, with automatic reset on success
**Request logging middleware** — every HTTP request is logged asynchronously via Celery to MongoDB
**Global exception handling** — custom exception classes with structured JSON error responses
**Flower monitoring UI** — visual dashboard for inspecting Celery workers and tasks

---

## Project Setup

### Prerequisites

Docker & Docker Compose
Python 3.10+ (only needed for local development without Docker)

### Clone & Run

```bash
git clone https://github.com/suchit-hirani-python-ak/Multi_source_scrapper_and_aggregrator.git
cd Multi_source_scrapper_and_aggregrator
```

---

## Docker Commands

Build and start all services (app, Redis, Celery worker, Flower):

```bash
docker compose up -d --build
```

Stream logs from all containers:

```bash
docker compose logs -f
```

Stop all services:

```bash
docker compose down
```

---

## Environment Variables

Create a `.env` file in the project root with the following keys:

```env
MONGO_URL=mongodb+srv://<user>:<password>@cluster.mongodb.net/<dbname>
REDIS_URL=redis://redis:6379/0

ALGORITHM=HS256
ACCESS_TOKEN=<your-secret-key>
REFRESH_TOKEN=<your-refresh-secret-key>
ACCESS_EXPIRE_IN_MINUTES=30
REFRESH_EXPIRE_IN_DAYS=7
ENCRIPTION=bcrypt

ADMIN_NAME=<admin-username>
ADMIN_PASS=<admin-password>
```

---

## API Reference

### Authentication — `/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register a new user |
| `POST` | `/auth/login` | Public | Login; returns access + refresh tokens |
| `POST` | `/auth/refresh` | Public | Exchange a valid refresh token for a new token pair |
| `POST` | `/auth/setup-root` | Header credentials | Create a new admin account |
| `DELETE` | `/auth/delete` | Bearer token | Delete the currently authenticated user's account |

### Scraping — `/scrape`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/scrape/` | User | Submit a new scraping job |
| `GET` | `/scrape/jobs/{job_id}` | User | Get status and progress of a job |
| `GET` | `/scrape/jobs/{job_id}/results` | User | Retrieve paginated results for a completed job |
| `GET` | `/scrape/jobs` | Admin | List all jobs (filterable by `status` and `site`) |
| `POST` | `/scrape/jobs/{job_id}/cancel` | User | Cancel a running job |

---

## Folder Structure

```
├── main.py                      # FastAPI app entry point, lifespan, middleware, routers
├── pyproject.toml               # Project metadata and dependencies (uv)
├── Dockerfile
├── docker-compose.yml
│
└── app/
    ├── core/
    │   ├── config.py            
    │   └── security.py          
    │
    ├── db/
    │   ├── base.py             
    │   └── session.py           
    │
    ├── dependencies/
    │   └── dependency.py        
    │
    ├── exception/
    │   └── error.py             
    │
    ├── middleware/
    │   └── log_middleware.py    
    │
    ├── repositories/            
    │   ├── job_repository.py
    │   ├── log_repository.py
    │   ├── token_repository.py
    │   └── user_repository.py
    │
    ├── routes/
    │   ├── jobscrape_route.py   
    │   └── user_route.py        
    │
    ├── schemas/                 
    │   ├── scraper.py
    │   ├── users.py
    │   ├── token.py
    │   ├── refresh.py
    │   └── logs.py
    │
    ├── scrapers/                
    │   ├── bookscrape.py        
    │   ├── quotescrape.py       
    │   ├── wikipediascrape.py   
    │   ├── yahooscrape.py       
    │   └── ycombinatorscrape.py 
    │
    ├── services/                
    │   ├── jobscrape_service.py
    │   ├── log_service.py
    │   └── user_service.py
    │
    └── utils/
        ├── celery.py            
        ├── job_control.py       
        └── redishelper.py       
```
---

## Architecture & Key Concepts

### Scraping Job Lifecycle

A user sends a `POST /scrape/` request specifying the target site, item limit, and optional categories.
The service creates a job record in MongoDB and dispatches a Celery task, returning a `job_id` immediately.
The Celery worker runs the scraper, streaming partial results into Redis as they arrive and updating job progress.
The user polls `GET /scrape/jobs/{job_id}` for status or `GET /scrape/jobs/{job_id}/results` for paginated data.
Jobs can be cancelled mid-run via `POST /scrape/jobs/{job_id}/cancel`; the worker checks for a cancellation flag in Redis before each page fetch.

### Refresh Token Security

On login, the user receives a short-lived access token and a long-lived refresh token.
Each user record holds a `token_version` counter in MongoDB.
When `/auth/refresh` is called, the service verifies that `token_version` in the token matches the stored value. If the stored version is higher (e.g. after a password reset or forced logout), the token is rejected.
On successful rotation, `token_version` is incremented and a fresh token pair is issued, invalidating all previous refresh tokens.

### Request Logging

An ASGI middleware wraps every incoming request.
Log records (path, method, status code, duration) are persisted asynchronously to MongoDB via a Celery task, keeping request latency unaffected.

### Docker Compose Services

| Service | Role |
|---|---|
| `redis` | Redis 7 (Alpine) — job state, caching, Celery broker & result backend |
| `app` | FastAPI application (hot-reload enabled for development) |
| `celery_worker` | Celery worker consuming tasks from the Redis broker |
| `flower` | Celery monitoring dashboard |

The `app` and `celery_worker` services both use `depends_on: redis` to ensure Redis is ready before they start.
