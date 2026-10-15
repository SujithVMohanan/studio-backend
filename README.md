# Studio Booking API

A backend for a fitness studio: staff schedule classes and grant credit packs, members spend credits to book classes, join a waitlist when a class is full, and cancel with a refund if they cancel before the studio's cutoff.

Built with Django 5.2, Django REST Framework, PostgreSQL 16 and JWT authentication.

---

## Contents

1. [Run with Docker (step by step)](#run-with-docker-step-by-step)
2. [Run without Docker (step by step)](#run-without-docker-step-by-step)
3. [Tests, linting and type checks](#tests-linting-and-type-checks)
4. [API step by step](#api-step-by-step)
5. [Postman collection](#postman-collection)
6. [Main flow walkthrough](#main-flow-walkthrough)
7. [Architecture](#architecture)
8. [Design patterns](#design-patterns)
9. [Decisions and trade-offs](#decisions-and-trade-offs)
10. [CI](#ci)

---

## Run with Docker (step by step)

### Step 1: Install Docker

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with the Compose plugin) and start it. Check it's running:

```bash
docker info
```

### Step 2: Get the code

```bash
git clone https://github.com/SujithVMohanan/studio-backend.git
cd studio-backend
```

### Step 3: Start the stack

```bash
docker compose up --build -d
```

This starts PostgreSQL and waits until it's healthy. Then `entrypoint.sh` runs the migrations, loads the demo data and starts the API on port 8000. `-d` runs it in the background, so you can close the terminal.

No `.env` file is needed for Docker. If one exists, Compose reads the values from it; otherwise it uses working defaults.

**How the image is built.** The `Dockerfile` has two stages:
1. **builder** installs the pinned dependencies into a virtual environment at `/opt/venv`.
2. **runtime** copies only that virtual environment and the code into a clean `python:3.13-slim` image, and runs as a non-root `app` user.

The image includes the dev tools (pytest, ruff, mypy), so the tests and checks below run in the same container.

`entrypoint.sh` runs migrate, seed and the server only for the default `serve` command. Any other command, such as `pytest`, runs directly without touching the database setup.

### Step 4: Check it's running

```bash
docker compose ps
```

`db` should show `healthy` and `web` should show `running`. If `web` isn't running, check its logs:

```bash
docker compose logs web
```

### Step 5: Open the API docs

| What | URL |
|---|---|
| Swagger UI | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/docs/redoc/ |
| OpenAPI JSON | http://localhost:8000/api/docs/json/ |
| Django admin | http://localhost:8000/admin/ |

### Step 6: Log in with a demo account

Every demo account uses the password `StudioDemo#2026`.

| Email | Role | Credits |
|---|---|---|
| `staff@studio.test` | staff | none |
| `member.a@studio.test` | member | 3 (expires in 7 days) + 10 (expires in 30 days) |
| `member.b@studio.test` | member | 10 |
| `member.c@studio.test` | member | 2 |
| `member.d@studio.test` | member | 5 |

The demo data also includes two studios in different time zones:
- **Downtown Yoga:** `America/New_York`, 4-hour cancellation cutoff.
- **Kochi Strength Lab:** `Asia/Kolkata`, 6-hour cutoff.

Each studio gets two classes a day for the next three days, both at studio-local times:
- **07:00:** 10 spots, costs 1 credit.
- **18:00:** 2 spots, costs 2 credits. It fills quickly, which makes it easy to try the waitlist.

Each studio also gets one class starting within its cutoff window, for trying a cancellation that forfeits the credits.

In Swagger, call `POST /api/users/login/`, copy `data.access`, click **Authorize**, and enter `Bearer <access token>`.

### Step 7 (optional): Create a superuser

```bash
docker compose exec web python manage.py createsuperuser
```

It asks for an email and a password. Superusers get the staff role and pass every role check, for both staff and member endpoints. Use the account at http://localhost:8000/admin/ or through the login API.

### Step 8: Run the tests

```bash
docker compose run --rm web pytest
```

### Step 9: Stop the stack

```bash
docker compose down        # stop (the database is kept)
docker compose down -v     # stop and wipe the database
```

### Other useful commands

```bash
docker compose logs -f web                                                   # follow the API logs
docker compose run --rm web sh -c "ruff check . && mypy apps core config"    # lint and type check
docker compose exec web python manage.py seed_demo                           # reseed (safe to rerun)
```

The seed is safe to rerun. It skips the fixture if the demo users already exist, and it skips classes and credit packs that are already there.

---

## Run without Docker (step by step)

### Step 1: Install the requirements

Python 3.13 and PostgreSQL 16.

### Step 2: Create a database

```sql
CREATE DATABASE studio;
```

### Step 3: Create a virtual environment and install dependencies

```bash
python -m venv venv
# Windows: .\venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
```

### Step 4: Configure the environment

```bash
cp .env-example .env
```

Fill in `SECRET_KEY` and the `DB_*` values.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SECRET_KEY` | yes | none | Django secret, also used to sign JWTs and encoded IDs |
| `DEBUG` | no | `False` | Set `True` locally; `seed_demo` refuses to run without it unless you pass `--force` |
| `ALLOWED_HOSTS` | no | `localhost,127.0.0.1` | Comma-separated |
| `CSRF_TRUSTED_ORIGINS` | no | empty | Comma-separated |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | yes | none | |
| `DB_HOST` / `DB_PORT` | no | `localhost` / `5432` | |
| `DB_CONN_MAX_AGE` | no | `60` | Persistent connection lifetime in seconds |
| `TIME_ZONE` | no | `Asia/Kolkata` | Server time zone. Business rules use each studio's own time zone |
| `CORS_ALLOWED_ORIGINS` | no | empty | Comma-separated |
| `SWAGGER_DEFAULT_API_URL` | no | `http://localhost:8000` | Base URL shown in Swagger |

### Step 5: Create the tables and load the demo data

```bash
python manage.py migrate
python manage.py seed_demo
```

### Step 6 (optional): Create a superuser

```bash
python manage.py createsuperuser
```

### Step 7: Start the server

```bash
python manage.py runserver
```

Open http://localhost:8000/api/docs/.

---

## Tests, linting and type checks

```bash
pytest                       # 120 tests
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
| Access control | Requests without a token are rejected; members can't call staff endpoints, staff can't call member endpoints; superusers pass both |
| End to end | Authenticate, grant credits, book, fill the class, join the waitlist, cancel, then automatic promotion |

The concurrency tests use real database transactions and threads (`@pytest.mark.django_db(transaction=True)`), so they exercise PostgreSQL row locks rather than mocks.

---

## API step by step

### Before you start

**Base URL:** `http://localhost:8000`

**Auth header** for every endpoint not marked "public":

```text
Authorization: Bearer <access token>
```

**Response envelope:** every endpoint returns:

```json
{ "status": true, "status_code": 200, "message": "...", "data": { }, "errors": { } }
```

Errors also include a machine-readable `"code"`, for example `"CLASS_FULL"`.

**Pagination:** list endpoints accept `page` (default 1) and `limit` (default 20, maximum 100). They return:

```json
"data": { "links": { "next": "", "previous": "" }, "count": 0, "results": [] }
```

**IDs:** every `uid` and `*_uid` value is a 22-character token you copy from an earlier response. Database IDs are never exposed.

**Dates and times:** datetimes are ISO 8601 with an offset (`2026-10-20T18:00:00Z` or `2026-10-20T18:00:00+05:30`). Dates are `YYYY-MM-DD`. In a URL, encode `+` as `%2B`.

### Quick reference

| Step | Method | URL | Who |
|---|---|---|---|
| 1.1 | POST | `/api/users/register/` | public |
| 1.2 | POST | `/api/users/login/` | public |
| 1.3 | POST | `/api/users/refresh/` | public |
| 1.4 | GET | `/api/users/me/` | logged in |
| 1.5 | POST | `/api/users/logout/` | logged in |
| 2.1 | GET | `/api/users/get-users/` | staff |
| 2.2 | DELETE | `/api/users/delete-users/` | staff |
| 3.1 | POST | `/api/studios/create-studio/` | staff |
| 3.2 | PATCH | `/api/studios/update-studio/<studio_uid>/` | staff |
| 3.3 | GET | `/api/studios/get-studios/` | logged in |
| 4.1 | POST | `/api/classes/create-class/` | staff |
| 4.2 | GET | `/api/classes/get-classes/` | logged in |
| 5.1 | POST | `/api/credits/grant-credit-pack/` | staff |
| 5.2 | GET | `/api/credits/get-balance/` | member |
| 5.3 | GET | `/api/credits/get-balance-at/` | member |
| 5.4 | GET | `/api/credits/get-ledger/` | member |
| 6.1 | POST | `/api/bookings/create-booking/` | member |
| 6.2 | GET | `/api/bookings/get-bookings/` | member |
| 6.3 | POST | `/api/bookings/cancel-booking/<booking_uid>/` | member |
| 7.1 | POST | `/api/bookings/join-waitlist/` | member |
| 7.2 | POST | `/api/bookings/leave-waitlist/` | member |
| 7.3 | GET | `/api/bookings/get-waitlist/` | member |

"Member" endpoints also accept superusers. Staff accounts that aren't superusers get `403` on them, and members get `403` on staff endpoints.

---

### Step 1: Authentication

#### 1.1 Register (public)

`POST /api/users/register/`

| Body field | Type | Required | Rules |
|---|---|---|---|
| `email` | string | yes | Valid email, unique (case-insensitive) |
| `full_name` | string | no | Up to 255 characters |
| `password` | string | yes | Must pass Django's password validators |
| `confirm_password` | string | yes | Must equal `password` |

```json
{
  "email": "john@example.com",
  "full_name": "John Doe",
  "password": "Str0ng#Pass2026",
  "confirm_password": "Str0ng#Pass2026"
}
```

**201** returns `data: { token_type, access, refresh, user: { uid, full_name, email, role, is_active, date_joined } }`. New users always get the `member` role, and the response logs them in straight away.

**Errors:** `400` for a duplicate email, mismatched passwords or a weak password; `429` when throttled.

#### 1.2 Login (public)

`POST /api/users/login/`

| Body field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `password` | string | yes |

```json
{ "email": "staff@studio.test", "password": "StudioDemo#2026" }
```

**200** returns the same shape as register. **Errors:** `401` for wrong credentials; `429` when throttled.

#### 1.3 Refresh the access token (public)

`POST /api/users/refresh/`

| Body field | Type | Required |
|---|---|---|
| `refresh` | string | yes |

```json
{ "refresh": "<refresh token>" }
```

**200** returns a new `access` token, and a new `refresh` token if rotation is enabled. **Errors:** `401` for an invalid or revoked token.

#### 1.4 Current user (logged in)

`GET /api/users/me/`

No parameters. **200** returns `uid, full_name, email, role, is_active, date_joined, is_staff, last_login`.

#### 1.5 Logout (logged in)

`POST /api/users/logout/`

| Body field | Type | Required | Notes |
|---|---|---|---|
| `refresh` | string | no | When sent, the refresh token is revoked too |

```json
{ "refresh": "<refresh token>" }
```

**200.** The current access token stops working immediately.

---

### Step 2: User management (staff)

#### 2.1 List users

`GET /api/users/get-users/`

| Query parameter | Type | Notes |
|---|---|---|
| `uid` | string | Exact user |
| `email` | string | Email filter |
| `name` | string | Name filter |
| `role` | `staff` or `member` | |
| `is_active` | `true` or `false` | |
| `page`, `limit` | int | Pagination |

Example: `/api/users/get-users/?role=member&limit=50`

#### 2.2 Delete users

`DELETE /api/users/delete-users/`

| Body field | Type | Required | Rules |
|---|---|---|---|
| `uids` | list of strings | yes | 1 to 100 user uids; duplicates are ignored |

```json
{ "uids": ["<user uid>", "<user uid>"] }
```

---

### Step 3: Studios

#### 3.1 Create studio (staff)

`POST /api/studios/create-studio/`

| Body field | Type | Required | Rules |
|---|---|---|---|
| `name` | string | yes | Up to 150 characters, unique |
| `timezone` | string | yes | IANA name such as `Asia/Kolkata` or `America/New_York` |
| `cancellation_cutoff_hours` | int | no | 0 or more, default 4 |

```json
{ "name": "Downtown Yoga", "timezone": "America/New_York", "cancellation_cutoff_hours": 4 }
```

**201** returns `uid, name, timezone, cancellation_cutoff_hours, created_at, updated_at`.

**Errors:** `400` for an invalid time zone; `409 STUDIO_NAME_TAKEN`.

#### 3.2 Update studio (staff)

`PATCH /api/studios/update-studio/<studio_uid>/`

Same fields as create, all optional; send only what you're changing.

```json
{ "cancellation_cutoff_hours": 6 }
```

**200.** **Errors:** `404` for an unknown studio; `409 STUDIO_NAME_TAKEN`.

#### 3.3 List studios (logged in)

`GET /api/studios/get-studios/`

| Query parameter | Type | Notes |
|---|---|---|
| `uid` | string | Exact studio |
| `name` | string | Name filter |
| `page`, `limit` | int | Pagination |

---

### Step 4: Classes

#### 4.1 Create class (staff)

`POST /api/classes/create-class/`

| Body field | Type | Required | Rules |
|---|---|---|---|
| `studio_uid` | string | yes | Studio uid |
| `starts_at` | datetime | yes | ISO 8601 with an offset |
| `duration_minutes` | int | yes | At least 1 |
| `spots` | int | yes | At least 1 |
| `credit_cost` | int | yes | 0 or more |

```json
{
  "studio_uid": "<studio uid>",
  "starts_at": "2026-10-20T18:00:00+05:30",
  "duration_minutes": 60,
  "spots": 2,
  "credit_cost": 2
}
```

**201** returns `uid, studio, starts_at, starts_at_local, ends_at, spots, spots_remaining, credit_cost, ...`

#### 4.2 Browse classes (logged in)

`GET /api/classes/get-classes/`

| Query parameter | Type | Required | Notes |
|---|---|---|---|
| `start` | datetime | yes, unless `uid` is given | Inclusive |
| `end` | datetime | yes, unless `uid` is given | Exclusive; must be after `start` |
| `studio_uid` | string | no | Only this studio |
| `uid` | string | no | One class; `start` and `end` aren't needed then |
| `page`, `limit` | int | no | Pagination |

Examples:

```text
/api/classes/get-classes/?start=2026-10-15T00:00:00Z&end=2026-10-20T00:00:00Z
/api/classes/get-classes/?start=2026-10-15T00:00:00Z&end=2026-10-20T00:00:00Z&studio_uid=<studio uid>
/api/classes/get-classes/?uid=<class uid>
```

Each class includes `spots_remaining`, which counts confirmed bookings.

---

### Step 5: Credits

#### 5.1 Grant a credit pack (staff)

`POST /api/credits/grant-credit-pack/`

| Body field | Type | Required | Rules |
|---|---|---|---|
| `member_uid` | string | yes | User uid of a member |
| `credits` | int | yes | At least 1 |
| `granted_on` | date | yes | `YYYY-MM-DD` |
| `expires_on` | date | yes | `YYYY-MM-DD`, on or after `granted_on` |

```json
{ "member_uid": "<user uid>", "credits": 10, "granted_on": "2026-10-15", "expires_on": "2026-11-15" }
```

**201** returns `uid, member_uid, credits, granted_on, expires_on, created_at`.

#### 5.2 Current balance (member)

`GET /api/credits/get-balance/`

No parameters. **200** returns `at, balance, packs[]`. Each pack has `uid, credits, remaining, granted_on, expires_on, is_active, is_expired`.

#### 5.3 Balance at a point in time (member)

`GET /api/credits/get-balance-at/`

| Query parameter | Type | Required |
|---|---|---|
| `at` | datetime | yes |

Example: `/api/credits/get-balance-at/?at=2026-10-15T10:00:00Z`. Returns the same shape as get-balance.

#### 5.4 Ledger history (member)

`GET /api/credits/get-ledger/`

| Query parameter | Type | Notes |
|---|---|---|
| `cause` | `grant`, `spend` or `refund` | Optional filter |
| `page`, `limit` | int | Pagination |

Each row has `uid, amount, cause, pack_uid, booking_uid, created_at`. Spends are negative; grants and refunds are positive.

---

### Step 6: Bookings

#### 6.1 Book a class (member)

`POST /api/bookings/create-booking/`

| Where | Field | Required | Rules |
|---|---|---|---|
| Header | `Idempotency-Key` | yes | 1 to 255 characters, unique per attempt, for example a UUID |
| Body | `class_uid` | yes | Class uid |

```text
Idempotency-Key: 7f0c2a9e-0d6b-4d1e-9a51-3b0f2b1a9c11
```

```json
{ "class_uid": "<class uid>" }
```

- **201** for a new booking: `uid, class_session, status, source, credits_charged, ...`
- **200** when retried with the same key: the original booking is returned and nothing is charged again.

**Errors:**
- `400 IDEMPOTENCY_KEY_REQUIRED`
- `404 CLASS_NOT_FOUND`
- `409` for `CLASS_FULL`, `ALREADY_BOOKED`, `CLASS_STARTED`, `INSUFFICIENT_CREDITS` or `IDEMPOTENCY_CONFLICT` (same key reused for a different class)

#### 6.2 My bookings (member)

`GET /api/bookings/get-bookings/`

| Query parameter | Type | Notes |
|---|---|---|
| `status` | `confirmed` or `cancelled` | Optional |
| `page`, `limit` | int | Pagination |

#### 6.3 Cancel a booking (member)

`POST /api/bookings/cancel-booking/<booking_uid>/`

No body. **200** returns the booking with `status: "cancelled"` and `cancellation_outcome`:
- `refunded` when cancelled before the studio's cutoff; the credits return to their original packs.
- `forfeited` when cancelled after the cutoff; no credits are returned.

Before the class starts, the first waitlisted member who can afford it is promoted automatically.

**Errors:** `404 BOOKING_NOT_FOUND` (including someone else's booking); `409 ALREADY_CANCELLED`.

---

### Step 7: Waitlist

#### 7.1 Join the waitlist (member)

`POST /api/bookings/join-waitlist/`

| Body field | Type | Required |
|---|---|---|
| `class_uid` | string | yes |

```json
{ "class_uid": "<class uid>" }
```

**201** returns `uid, class_session, status: "waiting", joined_at, ...`

**Errors:**
- `404 CLASS_NOT_FOUND`
- `409` for `SPOTS_AVAILABLE` (book instead), `ALREADY_BOOKED`, `ALREADY_WAITLISTED` or `CLASS_STARTED`

#### 7.2 Leave the waitlist (member)

`POST /api/bookings/leave-waitlist/`

| Body field | Type | Required |
|---|---|---|
| `class_uid` | string | yes |

**200** returns the entry with `status: "left"`. **Errors:** `404 NOT_WAITLISTED`.

#### 7.3 My waitlist entries (member)

`GET /api/bookings/get-waitlist/`

| Query parameter | Type | Notes |
|---|---|---|
| `status` | `waiting`, `promoted` or `left` | Optional |
| `page`, `limit` | int | Pagination |

Promoted entries include `booking_uid`, the booking that was created for that member.

---

### Error codes

| HTTP status | Code | When |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Invalid input; field details are in `errors` |
| 400 | `IDEMPOTENCY_KEY_REQUIRED` | Booking without an `Idempotency-Key` header |
| 400 | `EMAIL_ALREADY_EXISTS` | Registering with an email that's already used |
| 401 | `INVALID_CREDENTIALS` | Wrong email or password |
| 401 | `ACCOUNT_DISABLED` | The account has been deactivated |
| 401 | `INVALID_REFRESH_TOKEN` | Refresh token is invalid, expired, revoked or belongs to another user |
| 401 | none | Missing, expired or revoked access token |
| 403 | none | Wrong role |
| 404 | `STUDIO_NOT_FOUND`, `CLASS_NOT_FOUND`, `MEMBER_NOT_FOUND`, `BOOKING_NOT_FOUND`, `NOT_WAITLISTED` | |
| 409 | `CLASS_FULL` | No spots left |
| 409 | `ALREADY_BOOKED` | Member already has a confirmed booking for this class |
| 409 | `CLASS_STARTED` | Class already started |
| 409 | `INSUFFICIENT_CREDITS` | Not enough unexpired credits |
| 409 | `IDEMPOTENCY_CONFLICT` | Same key used for a different class |
| 409 | `ALREADY_CANCELLED` | Booking already cancelled |
| 409 | `ALREADY_WAITLISTED` | Already waiting for this class |
| 409 | `SPOTS_AVAILABLE` | Class isn't full; book instead |
| 409 | `STUDIO_NAME_TAKEN` | Duplicate studio name |
| 429 | none | Too many login, registration or refresh attempts (30 per minute) |

---

## Postman collection

The collection is in [`postman/Studio API.postman_collection.json`](postman/Studio%20API.postman_collection.json). Its requests are numbered in the order of the main flow, from **1.register** to **21.my-waitlist**.

### Step 1: Start the API

```bash
docker compose up --build -d
```

### Step 2: Import the collection

In Postman, click **Import** and choose `postman/Studio API.postman_collection.json`.

### Step 3: Check the collection variables

Open the collection, then the **Variables** tab:

| Variable | Default | Used for |
|---|---|---|
| `baseUrl` | `http://127.0.0.1:8000` | Every request. Change it if the API runs elsewhere. |
| `access_token` | empty | The collection's Bearer token, used by the auth, user, studio, class and credit-grant requests. Set it to a **staff** access token. |
| `member_access` | empty | The Bearer token for the member requests: balance, bookings and waitlist. Set it to a **member** access token. |

### Step 4: Log in as staff and as a member

1. Send **2.login** with `staff@studio.test` / `StudioDemo#2026`. Copy `data.access` into `access_token`.
2. Send **2.login** again with `member.a@studio.test` / `StudioDemo#2026`. Copy `data.access` into `member_access`.
3. Save the collection, so the variables are used.

Access tokens last 60 minutes. When one expires, log in again and update the variable.

### Step 5: Follow the flow

Run the requests in order:
1. **Staff:** create a studio (8), update it (9), create a class (11) and grant credits to a member (13).
2. **Member:** browse classes (12), check the balance (14) and book a class (15).
3. **Waitlist:** when the class is full, another member joins the waitlist (19). Log in as that member and put their token in `member_access` first.
4. **Cancel:** the booking member cancels (18), and the longest-waiting member who can afford it is promoted. Check with **16.my-booking** and **21.my-waitlist**.

Before you send a request:
- **Replace the IDs** saved in the requests (`studio_uid`, `class_uid`, `member_uid`, the booking ID in the cancel URL) with ones from your own responses, because IDs differ between databases. **6.list-users** gives member IDs, and **12.list-classes** gives class IDs.
- **Each booking gets a new `Idempotency-Key` automatically** (`{{$guid}}`). To test a retry, put a fixed value in the header and send it twice; the second call returns the original booking.
- **Use future dates.** Classes must start in the future, and **12.list-classes** needs a `start`/`end` range that includes them.

The point-in-time balance (`GET /api/credits/get-balance-at/?at=...`) and the ledger (`GET /api/credits/get-ledger/`) aren't in the collection. Try them in Swagger at http://localhost:8000/api/docs/, or import the OpenAPI spec below.

### Alternative: import from OpenAPI

The OpenAPI spec is generated from the code and served at `GET /api/docs/json/`. In Postman, **Import** that URL to get a request for every endpoint, always matching the current code.

---

## Main flow walkthrough

These steps use the demo data and run the whole booking lifecycle. Replace `<...>` with values from earlier responses.

### Step 1: Staff logs in

```http
POST /api/users/login/
{ "email": "staff@studio.test", "password": "StudioDemo#2026" }
```

Copy `data.access` and send it as `Authorization: Bearer <access>`.

### Step 2: Find a class

```http
GET /api/classes/get-classes/?start=2026-10-15T00:00:00Z&end=2026-10-20T00:00:00Z
```

Pick an evening class with 2 spots and copy its `uid`.

### Step 3: Staff grants credits (optional)

The demo members already have packs. To add more, find the member's `uid` with `GET /api/users/get-users/?role=member`, then:

```http
POST /api/credits/grant-credit-pack/
{ "member_uid": "<member uid>", "credits": 5, "granted_on": "2026-10-15", "expires_on": "2026-11-15" }
```

### Step 4: Two members fill the class

Log in as `member.a` and `member.b`, and have each book with their own key:

```http
POST /api/bookings/create-booking/
Idempotency-Key: <a new UUID>
{ "class_uid": "<class uid>" }
```

Each returns `201 Created`. Sending the same request again with the same key returns the original booking with `200 OK`, without a second charge. The class now has 0 spots remaining.

### Step 5: A third member joins the waitlist

As `member.d`:

```http
POST /api/bookings/create-booking/      →  409 CLASS_FULL
POST /api/bookings/join-waitlist/
{ "class_uid": "<class uid>" }          →  201 Created
```

### Step 6: A booked member cancels

As `member.a`:

```http
POST /api/bookings/cancel-booking/<booking uid>/
```

- **Before the studio's cutoff:** the outcome is `refunded`, and the credits go back to the packs they came from.
- **After the cutoff:** the outcome is `forfeited`, and no credits are returned.

In the same transaction, the first waitlisted member who can afford the class is booked automatically, and their credits are charged.

### Step 7: Check the results

```http
GET /api/bookings/get-waitlist/       (as member.d: the entry is now "promoted")
GET /api/bookings/get-bookings/       (as member.d: a booking with source "waitlist")
GET /api/credits/get-balance/         (current balance per pack)
GET /api/credits/get-ledger/          (every grant, spend and refund)
GET /api/credits/get-balance-at/?at=2026-10-15T09:00:00Z
```

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

### Public IDs

Database primary keys are never exposed. Every ID in the API is a 22-character token. Each token is an HMAC-signed, masked encoding of the primary key, scoped to one model, so:
- IDs can't be guessed or enumerated.
- A booking ID can't be passed off as a class ID.
- A tampered token returns a validation error instead of a database lookup.

### Authentication

- **Login** returns a JWT pair. Access tokens last 60 minutes; refresh tokens last 30 days.
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

**Expiry isn't a ledger movement.**
The ledger records grants, spends and refunds. When a pack expires, its unused credits leave the balance without a new ledger row. `GET /api/credits/get-balance/` explains the difference: it lists each pack with its `remaining` credits, `is_active` and `is_expired`, so the ledger total minus the remaining credits of inactive packs (expired, or not started yet) equals the balance.

---

## CI

`.github/workflows/ci.yml` runs on every push and pull request, against a PostgreSQL 16 service container:

1. `ruff check .`
2. `mypy apps core config` (strict)
3. `python manage.py makemigrations --check --dry-run` (fails if a model change has no migration)
4. `pytest`

All dependencies are pinned in `requirements.txt` and `requirements-dev.txt`.
