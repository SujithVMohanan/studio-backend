# Studio Booking API

A backend for a fitness studio: staff schedule classes and grant credit packs, members spend credits to book classes, join a waitlist when a class is full, and cancel with a refund if they cancel before the studio's cutoff.

Built with Django 5.2, Django REST Framework, PostgreSQL 16 and JWT authentication.

---

## Contents

1. [Quick start (Docker)](#quick-start-docker)
2. [Local setup (without Docker)](#local-setup-without-docker)
3. [Tests, linting and type checks](#tests-linting-and-type-checks)
4. [Architecture](#architecture)
5. [Design patterns](#design-patterns)
6. [Main flow walkthrough](#main-flow-walkthrough)
7. [API reference](#api-reference)
8. [Decisions and trade-offs](#decisions-and-trade-offs)
9. [CI](#ci)

---

## Quick start (Docker)

Requirements: Docker Desktop (or Docker Engine with the Compose plugin).

```bash
docker compose up --build -d
```

This starts PostgreSQL, runs the migrations, loads the demo data and starts the API on port 8000.

| What | Where |
|---|---|
| Swagger UI | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/docs/redoc/ |
| OpenAPI JSON | http://localhost:8000/api/docs/json/ |
| Django admin | http://localhost:8000/admin/ |

Run the test suite:

```bash
docker compose run --rm web pytest
```

Other useful commands:

```bash
docker compose logs -f web     # follow the API logs
docker compose ps              # container status
docker compose down            # stop (database is kept)
docker compose down -v         # stop and wipe the database
```

### Demo accounts

Loaded by `seed_demo`. Every account uses the password `StudioDemo#2026`.

| Email | Role | Credits |
|---|---|---|
| `staff@studio.test` | staff | none |
| `member.a@studio.test` | member | 3 (expires in 7 days) + 10 (expires in 30 days) |
| `member.b@studio.test` | member | 10 |
| `member.c@studio.test` | member | 2 |
| `member.d@studio.test` | member | 5 |

Two studios in different time zones:
- **Downtown Yoga:** `America/New_York`, 4-hour cancellation cutoff.
- **Kochi Strength Lab:** `Asia/Kolkata`, 6-hour cutoff.

Each studio gets two classes a day for the next three days, both at studio-local times:
- **07:00:** 10 spots, costs 1 credit.
- **18:00:** 2 spots, costs 2 credits. It fills quickly, which makes it easy to try the waitlist.

Each studio also gets one class starting within its cutoff window, for trying a cancellation that forfeits the credits.

The seed is safe to rerun. It skips the fixture if the demo users already exist, and it skips classes and credit packs that are already there.

### Create a superuser

```bash
docker compose exec web python manage.py createsuperuser
```

It asks for an email and a password. Superusers get the staff role and pass every role check, for both staff and member endpoints.

---

## Local setup (without Docker)

Requirements: Python 3.13 and PostgreSQL 16.

```bash
python -m venv venv
# Windows: .\venv\Scripts\activate    macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt

cp .env-example .env          # then fill in SECRET_KEY and the DB_* values
python manage.py migrate
python manage.py seed_demo    # requires DEBUG=True, or pass --force
python manage.py runserver
```

### Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SECRET_KEY` | yes | none | Django secret, also used to sign JWTs and encoded IDs |
| `DEBUG` | no | `False` | |
| `ALLOWED_HOSTS` | no | `localhost,127.0.0.1` | Comma-separated |
| `CSRF_TRUSTED_ORIGINS` | no | empty | Comma-separated |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | yes | none | |
| `DB_HOST` / `DB_PORT` | no | `localhost` / `5432` | |
| `DB_CONN_MAX_AGE` | no | `60` | Persistent connection lifetime in seconds |
| `TIME_ZONE` | no | `Asia/Kolkata` | Server time zone. Business rules use each studio's own time zone |
| `CORS_ALLOWED_ORIGINS` | no | empty | Comma-separated |
| `SWAGGER_DEFAULT_API_URL` | no | `http://localhost:8000` | Base URL shown in Swagger |

`docker-compose.yml` reads these from `.env` when it exists and falls back to working defaults when it doesn't. It always sets `DB_HOST=db` and `DEBUG=True`.

---

## Tests, linting and type checks

```bash
pytest                       # 119 tests
ruff check .                 # linter
mypy apps core config        # strict type checking
```

All three run in CI on every push. Configuration lives in `pyproject.toml`.

### What the tests cover

Tests live in `core/tests/`. Service-level tests pin the clock to a fixed instant so the time rules are deterministic. API tests go through the real HTTP layer.

| Area | Examples |
|---|---|
| Credits | Grant validation, soonest-expiry spending across packs, expired packs ignored, point-in-time balance, append-only ledger |
| Booking | Full class, already booked, class started, insufficient credits, idempotent retry, same key reused for a different class |
| Cancellation | Refund before the cutoff, forfeit after it, double-cancel rejected, refund goes back to the original packs |
| Time zones | Cutoff computed in studio-local wall-clock time, including across the New York DST change on 2026-11-01 |
| Waitlist | Join only when full, FIFO promotion on cancel, members who can't afford the class are skipped, no promotion after the class starts |
| Concurrency | Threads racing for the last spot (exactly one wins), concurrent retries with the same idempotency key (one booking, one charge) |
| Access control | Every endpoint checked for unauthenticated, member, staff and superuser access |
| End to end | Authenticate, grant credits, book, fill the class, join the waitlist, cancel, then automatic promotion |

The concurrency tests use real database transactions and threads (`@pytest.mark.django_db(transaction=True)`), so they exercise PostgreSQL row locks rather than mocks.

---

## Architecture

```text
studio-backend/
├── config/                 settings, root URLs, WSGI/ASGI
├── apps/
│   ├── users/              custom User (email login, staff/member role), JWT auth, seed_demo command
│   ├── studios/            Studio and ClassSession, scheduling and browsing
│   ├── credits/            CreditPack, append-only CreditLedger, allocation planner, balances
│   └── bookings/           Booking and WaitlistEntry, booking, cancellation, waitlist promotion
└── core/                   shared code used by every app
    ├── permissions/        IsStaffRole, IsMemberRole (superusers pass both)
    ├── exceptions/         BusinessConflict / ResourceNotFound and the global exception handler
    ├── responses/          a single response envelope for every endpoint
    ├── encryption/         opaque, tamper-proof public IDs
    ├── pagination/         page-number pagination
    ├── utils/              clock, JWT auth with blacklist, typed serializer fields
    ├── fixtures/           demo.json (users and studios, natural keys, no primary keys)
    ├── seeds/              demo seed logic
    └── tests/              pytest suite
```

Each app follows the same layers:

```text
urls.py → views.py → serializer.py → services/ → repository.py → models.py
           (HTTP)      (input)        (rules)      (queries)
                       schemas.py (output)
```

| Layer | Responsibility |
|---|---|
| `views.py` | HTTP only: permissions, parse input, call one service method, wrap the result in the response envelope |
| `serializer.py` | Validates input (types, ranges, encoded IDs, time-zone-aware datetimes) |
| `services/` | Business rules and transaction boundaries. Raises `BusinessConflict` or `ResourceNotFound` with a stable error code |
| `repository.py` | Every ORM query, including row locks (`select_for_update`) |
| `schemas.py` | Shapes output: encodes IDs, adds computed fields such as `spots_remaining` and `ends_at` |

### Response format

Every endpoint returns the same envelope:

```json
{
  "status": true,
  "status_code": 201,
  "message": "Created successfully",
  "data": { },
  "errors": { }
}
```

Errors add a machine-readable `code`:

```json
{
  "status": false,
  "status_code": 409,
  "message": "This class is full.",
  "data": {},
  "errors": {},
  "code": "CLASS_FULL"
}
```

| HTTP status | When |
|---|---|
| 400 | Validation errors (`VALIDATION_ERROR`, `IDEMPOTENCY_KEY_REQUIRED`) |
| 401 | Missing, expired or revoked token |
| 403 | Wrong role |
| 404 | `CLASS_NOT_FOUND`, `BOOKING_NOT_FOUND`, `NOT_WAITLISTED` |
| 409 | Business rule conflicts: `CLASS_FULL`, `ALREADY_BOOKED`, `CLASS_STARTED`, `INSUFFICIENT_CREDITS`, `ALREADY_CANCELLED`, `ALREADY_WAITLISTED`, `SPOTS_AVAILABLE`, `IDEMPOTENCY_CONFLICT`, `STUDIO_NAME_TAKEN` |
| 429 | Too many login, registration or refresh attempts |

### Public IDs

Database primary keys are never exposed. Every ID in the API (`uid`, `class_uid`, `studio_uid`, `member_uid`, `booking_uid`) is a 22-character token. Each token is an HMAC-signed, masked encoding of the primary key, scoped to one model, so:
- IDs can't be guessed or enumerated.
- A booking ID can't be passed off as a class ID.
- A tampered token returns a validation error instead of a database lookup.

### Authentication

- **Login** returns a JWT pair. Access tokens last 15 minutes; refresh tokens last 30 days.
- **Logout** revokes the refresh token and also blacklists the current access token until it expires, so it can't be used again after logout.
- **Login, registration and token refresh** are rate-limited to 30 requests per minute per client.
- **Login takes the same time whether or not the email exists.** An unknown email still costs one password-hash check, so response timing doesn't reveal which emails are registered.

---

## Design patterns

| Pattern | Where | Why |
|---|---|---|
| **Service layer** | `apps/*/services/` | Business rules live in plain functions with explicit inputs, including an injectable `now`. Views stay thin, and rules are tested without HTTP. |
| **Repository** | `apps/*/repository.py` | Queries and locks are in one place per app, so services read as rules rather than ORM chains, and lock ordering is easy to audit. |
| **Append-only ledger (event-sourcing style)** | `CreditLedger` | Every credit movement (grant, spend, refund) is a new row. Rows can't be updated or deleted, enforced in `save()`/`delete()`. Balances are always derived from the ledger, which gives a complete audit trail and makes point-in-time balances a simple query. |
| **Strategy / planner** | `credits/services/allocation.py` | `plan_allocation` decides which packs pay for a booking (soonest expiry first) separately from `record_spend`, which writes it. Waitlist promotion reuses the planner to check affordability before creating anything. |
| **Pessimistic locking** | `ClassSessionRepository.lock_by_id`, credit pack locks | `SELECT ... FOR UPDATE` on the class row serialises booking, cancellation and promotion for that class, so capacity can't be oversold. |
| **Idempotency key** | `POST /api/bookings/create-booking/` | Retries return the original booking instead of charging twice, backed by a unique database constraint. |
| **Database constraints as the last line of defence** | Unique and check constraints on bookings, waitlist, ledger, packs and classes | Even if a code path is wrong, the database rejects double bookings, duplicate waitlist entries, negative grants and ledger rows whose sign doesn't match their cause. |
| **Injectable clock** | `core/utils/clock.py` | Services take `now` as an argument, so time zone and DST rules are tested at exact instants. |
| **Custom permissions** | `core/permissions/` | Role checks are declared per view (`IsStaffRole`, `IsMemberRole`) rather than written as `if` statements in handlers. |

---

## Main flow walkthrough

All requests below use the demo data. Replace `<...>` with values from earlier responses.

**1. Staff logs in**

```http
POST /api/users/login/
{ "email": "staff@studio.test", "password": "StudioDemo#2026" }
```

Returns `access` and `refresh` tokens. Send `Authorization: Bearer <access>` on every following request.

**2. Find a class**

```http
GET /api/classes/get-classes/?start=2026-10-15T00:00:00Z&end=2026-10-20T00:00:00Z
```

Each class shows `spots`, `spots_remaining`, `credit_cost`, `starts_at` and `ends_at`. Pick an evening class with 2 spots.

**3. Staff grants credits** (optional: the demo members already have packs)

```http
POST /api/credits/grant-credit-pack/
{ "member_uid": "<member uid>", "credits": 5, "granted_on": "2026-10-15", "expires_on": "2026-11-15" }
```

Find member IDs with `GET /api/users/get-users/?role=member`.

**4. Two members fill the class**

Log in as `member.a` and `member.b`, and have each book:

```http
POST /api/bookings/create-booking/
Idempotency-Key: 7f0c2a9e-0d6b-4d1e-9a51-3b0f2b1a9c11
{ "class_uid": "<class uid>" }
```

The response is `201 Created`. Sending the same request again with the same key returns the original booking with `200 OK`, without a second charge. The class now has 0 spots remaining.

**5. A third member joins the waitlist**

As `member.d`:

```http
POST /api/bookings/create-booking/      →  409 CLASS_FULL
POST /api/bookings/join-waitlist/
{ "class_uid": "<class uid>" }          →  201 Created
```

**6. A booked member cancels**

As `member.a`:

```http
POST /api/bookings/cancel-booking/<booking uid>/
```

- **Before the studio's cutoff:** the outcome is `refunded`, and the credits go back to the packs they came from.
- **After the cutoff:** the outcome is `forfeited`, and no credits are returned.

In the same transaction, the first waitlisted member who can afford the class is booked automatically, and their credits are charged.

**7. Check the results**

```http
GET /api/bookings/get-bookings/       (as member.d: a booking with source "waitlist")
GET /api/bookings/get-waitlist/       (as member.d: the entry is now "promoted")
GET /api/credits/get-balance/         (current balance per pack)
GET /api/credits/get-ledger/          (every grant, spend and refund)
GET /api/credits/get-balance-at/?at=2026-10-15T09:00:00Z
```

---

## API reference

Full schemas are in Swagger at `/api/docs/`.

| Method | Path | Access |
|---|---|---|
| POST | `/api/users/register/` | public |
| POST | `/api/users/login/` | public |
| POST | `/api/users/refresh/` | public |
| POST | `/api/users/logout/` | authenticated |
| GET | `/api/users/me/` | authenticated |
| GET | `/api/users/get-users/` | staff |
| POST | `/api/users/delete-users/` | staff |
| POST | `/api/studios/create-studio/` | staff |
| PUT/PATCH | `/api/studios/update-studio/<studio_uid>/` | staff |
| GET | `/api/studios/get-studios/` | authenticated |
| POST | `/api/classes/create-class/` | staff |
| GET | `/api/classes/get-classes/?start=&end=&studio_uid=` | authenticated |
| POST | `/api/credits/grant-credit-pack/` | staff |
| GET | `/api/credits/get-balance/` | member |
| GET | `/api/credits/get-balance-at/?at=` | member |
| GET | `/api/credits/get-ledger/?cause=` | member |
| POST | `/api/bookings/create-booking/` (header `Idempotency-Key`) | member |
| GET | `/api/bookings/get-bookings/?status=` | member |
| POST | `/api/bookings/cancel-booking/<booking_uid>/` | member |
| POST | `/api/bookings/join-waitlist/` | member |
| POST | `/api/bookings/leave-waitlist/` | member |
| GET | `/api/bookings/get-waitlist/?status=` | member |

"Member" endpoints also accept superusers.

### API collection

The OpenAPI spec is generated from the code and served at `GET /api/docs/json/`. Import it into Postman with **Import → Link** to get every endpoint with its request schema.

---

## Decisions and trade-offs

**Cancellation cutoff uses the studio's local wall clock.**
The deadline is "class start minus N hours" computed in the studio's time zone. Across a DST change, a 4-hour cutoff for a 09:00 class is always 05:00 local time, even though the night is an hour shorter or longer. Members think in local time, and this matches what the studio would tell them.

**Refunds go back to the packs they came from.**
A refund writes one ledger row per pack that was charged, reversing the original spend. If a pack has expired by then, those credits stay expired. Refunding into a newer pack would quietly extend expiry dates.

**Credits are spent soonest-expiry first.**
This uses up credits that would otherwise expire first, which is best for the member. Ties are broken by pack ID so the order is deterministic.

**The waitlist skips members who can't afford the class, but keeps their place.**
On cancellation, the queue is walked in join order and the first member with enough credits is promoted. Members without enough credits stay `waiting` in their original position, so a later top-up can still get them promoted.

**No promotion after the class has started.**
A cancellation after the start time still applies the forfeit rule, but nobody is promoted into a class that's already running.

**Joining the waitlist requires the class to be full.**
If there's a free spot, the API returns `SPOTS_AVAILABLE` and the member should book instead. A member who books directly is removed from that class's waitlist.

**Idempotency keys are scoped to each member.**
Two members can use the same key without conflict. Reusing a key for a different class returns `IDEMPOTENCY_CONFLICT` rather than quietly returning the wrong booking. The key is checked again after the class lock is taken, so two concurrent retries with the same key produce one booking and one charge.

**Capacity is protected by row locks, not optimistic retries.**
Booking a class is a short, high-contention operation on a single row. Locking the class row keeps the code simple and correct. A unique constraint on (member, class) for confirmed bookings is the backstop.

**Balances are computed from the ledger, not stored.**
There's no running-balance column that could drift out of sync. Indexes on (member, created_at) and (pack, created_at) keep the queries fast.

**Expiry is a calendar date in UTC.**
A pack with `expires_on = 2026-11-15` can be spent up to and including that UTC date.

---

## CI

`.github/workflows/ci.yml` runs on every push and pull request, against a PostgreSQL 16 service container:

1. `ruff check .`
2. `mypy apps core config` (strict)
3. `python manage.py makemigrations --check --dry-run` (fails if a model change has no migration)
4. `pytest`

All dependencies are pinned in `requirements.txt` and `requirements-dev.txt`.
