# ZNPHI Fleet Manager — Technical Handover

## Overview

ZNPHI Fleet Manager is a Django 5 web application for managing transport logistics at the Zambia National Public Health Institute. It covers the full lifecycle of a transport request: submission by ZNPHI staff, review and vehicle/driver assignment by the Fleet Manager, maintenance tracking, and a KPI dashboard with a choropleth map. The codebase is a complete standalone prototype (229 passing tests) designed for integration into the existing ZNPHI implementation tracker.

---

## Repository Layout

```
fleet_project/     Django project root — settings.py, urls.py, wsgi.py
accounts/          Auth, 4 role groups, GroupRequiredMixin, context processors
bookings/          TransportRequest workflow, Province/District/Department models
fleet/             Vehicle, Driver, FuelRecord, MaintenanceRecord
dashboard/         KPI dashboard, Gantt chart, Leaflet choropleth, district JSON API
settings_app/      Singleton Settings model — configurable thresholds and email
templates/         All HTML templates (base.html + per-app subdirectories)
static/            Tailwind/DaisyUI CSS, Chart.js, geojson/zambia_districts.geojson
geo_data/          District boundary GeoJSON files — gitignored (see below)
.github/           CI workflow (tests.yml)
documentation/     This file
```

> **`geo_data/` is gitignored** due to file size. The district boundary shapefiles/GeoJSON used by the Leaflet choropleth map were sourced from the UN OCHA Humanitarian Data Exchange:
> https://data.humdata.org/dataset/cod-ab-zmb
>
> Download the Zambia Administrative Boundaries dataset (COD-AB), convert the district-level shapefile to GeoJSON, and place it in `geo_data/` before running the application. The dashboard map view will fail to render district polygons without this file.

---

## Data Model

### bookings app

**`Province`** — `name` (unique). 10 Zambian provinces, loaded from fixture at setup.

**`District`** — `name`, `province` (FK → Province). 116 districts, loaded from fixture.

**`Department`** — `name` (unique). ZNPHI organisational units. Add/edit via Django admin.

**`TransportRequest`** — central model.

| Field | Type | Notes |
|---|---|---|
| `requester_name` | CharField | Full name of the traveller |
| `department` | FK → Department | Protected on delete |
| `position` | CharField | Job title |
| `programme_activity` | CharField | Activity description |
| `date_of_request` | DateField | Auto-set on creation |
| `period_from` | DateField | Trip start |
| `period_to` | DateField | Trip end |
| `province` | FK → Province | Protected on delete |
| `district` | FK → District | Protected on delete |
| `destination` | CharField | Specific destination within district |
| `num_vehicles` | PositiveIntegerField | Default 1 |
| `num_drivers` | PositiveIntegerField | Default 1 |
| `num_passengers` | PositiveIntegerField | Default 1 |
| `is_emergency` | BooleanField | Surfaces at top of queue |
| `status` | CharField | Submitted / Approved / Rejected / In Progress / Completed / Cancelled |
| `admin_comment` | TextField | Fleet Manager rejection note, optional |
| `coordination_acknowledged` | BooleanField | True once the requester accepts the nudge warning |
| `coordination_note` | TextField | Requester's explanation if acknowledging the nudge |
| `approved_date` | DateField | Nullable |
| `submitted_by` | FK → User | Nullable, SET_NULL on user deletion |

Property: `is_late_booking` — True when `period_from - today < 14 days`.

**`TripAssignment`** — `transport_request` (FK), `vehicle` (FK), `driver` (FK). One row per vehicle/driver pair. A request requiring 3 vehicles produces 3 `TripAssignment` rows pointing to the same request.

---

### fleet app

**`Vehicle`**

| Field | Type / Choices | Notes |
|---|---|---|
| `make`, `model` | CharField | |
| `year` | PositiveIntegerField | |
| `license_plate` | CharField, unique | |
| `vehicle_type` | Hilux / Land Cruiser | |
| `current_mileage` | PositiveIntegerField | Odometer reading in km |
| `seating_capacity` | PositiveIntegerField | |
| `fuel_type` | Diesel / Petrol | |
| `status` | Available / On Trip / In Maintenance / Emergency Standby | |
| `maintenance_interval_km` | PositiveIntegerField | Default 5000; per-vehicle override |
| `last_service_date` | DateField, nullable | Auto-updated by signal |
| `last_service_mileage` | PositiveIntegerField, nullable | Auto-updated by signal |

Properties:
- `km_until_service` → `(last_service_mileage + maintenance_interval_km) - current_mileage`. Returns `None` if no service record exists.
- `maintenance_status` → `green` (> 500 km), `amber` (≤ 500 km), `red` (< 0 km — overdue), `unknown` (no service record).

A `post_save` signal on `MaintenanceRecord` keeps `Vehicle.last_service_date` and `last_service_mileage` in sync with the most recent record. Deleting or back-dating a record stays consistent because the signal re-queries for the latest rather than using the instance directly.

**`Driver`** — `name`, `phone` (optional), `status` (Available / On Assignment / On Leave).

**`FuelRecord`** — FK → Vehicle. Fields: `date`, `liters`, `cost_per_liter`, `total_cost`, `location`, `mileage_at_fillup`, `notes`.

**`MaintenanceRecord`** — FK → Vehicle. Fields: `date`, `mileage_at_service`, `service_type`, `cost`, `vendor`, `notes`.

---

### settings_app

**`Settings`** — singleton; always `pk=1`. Never query directly; use `Settings.load()`.

| Field | Default | Purpose |
|---|---|---|
| `email_notifications_enabled` | False | Toggle new-request email alerts |
| `notification_email` | blank | Recipient address |
| `buffer_days` | 1 | Padding days around existing bookings when checking vehicle/driver availability |
| `nudge_mode` | `7day` | `exact` / `7day` / `custom` — window for coordination nudge |
| `nudge_custom_days` | 7 | Used when `nudge_mode == custom` |
| `default_maintenance_interval_km` | 5000 | Applied to newly created vehicles |

`Settings.nudge_window_days()` returns the effective window in days based on the current mode.

> **Singleton enforcement:** `Settings.save()` sets `self.pk = 1` before every write. `Settings.load()` uses `get_or_create(pk=1)`. The admin prevents adding a second row or deleting the existing one.

---

### A note on seed data

The repository includes management commands (`seed_data`, `flush_seed`) that populate the database with synthetic prototype data: 23 vehicles, 20 drivers, 334 transport requests, 136 fuel records, 65 maintenance records, and 16 demo user accounts (prefixed `seed_`). **This data is for demonstration only.** Real vehicle records and historical request data — currently held on paper at Monze — will need to be entered through the UI or admin panel. Run `python manage.py flush_seed --no-input` to clear all synthetic data before going live.

---

## Role & Permission System

Four Django `auth.Group` names drive all access control. These groups must exist in the database (see setup instructions).

| Group | Landing page | Permissions |
|---|---|---|
| **Requester** | My Requests | Submit requests; view and cancel own requests (Submitted, Approved, In Progress only) |
| **Fleet Manager** | Request Queue | All of the above + review/approve/reject requests, assign vehicles and drivers, manage vehicle and driver records, view dashboard and Gantt chart, edit system settings |
| **Dashboard Viewer** | Dashboard | Submit requests; view own requests; read-only access to vehicles, drivers, Gantt chart, KPI dashboard |
| **Superadmin** | User Management | Everything Fleet Manager can + create user accounts and assign roles |

**`GroupRequiredMixin`** (`accounts/mixins.py`) is applied to every class-based view. Set `group_required = ['Group A', 'Group B']`. Unauthenticated users are redirected to `LOGIN_URL`; authenticated users in the wrong group receive a 403.

**Context processors** — both must be registered in `TEMPLATES[0]['OPTIONS']['context_processors']`:

- `accounts.context_processors.user_roles` — injects `is_requester`, `is_fleet_manager`, `is_dashboard_viewer`, `is_superadmin` into every template context.
- `bookings.context_processors.pending_request_count` — injects `pending_request_count` (Submitted requests) for the nav badge; only computed for Fleet Manager and Superadmin.

---

## Core Application Logic

### Coordination nudge
`bookings/views.py: get_overlapping_trips(district, period_from, period_to, nudge_days)`

On new request submission, the view queries for existing Approved or In Progress requests to the same district whose date ranges overlap the requested period, expanded by `nudge_days` on each side. If any are found, the user is redirected to a separate acknowledgment view (`bookings:coordination_nudge`) before the request is saved. The nudge window is read from `Settings.load().nudge_window_days()` at request time so it responds to configuration changes without a redeploy.

### Vehicle and driver availability filtering
`bookings/views.py: get_available_vehicles(period_from, period_to, buffer_days)`
`bookings/views.py: get_available_drivers(period_from, period_to, buffer_days)`

Excludes records with overlapping `TripAssignment` entries — where the overlap check includes `buffer_days` padding on both sides of the requested period. Additionally excludes vehicles where `maintenance_status == 'red'`. Buffer days are read from `Settings.load().buffer_days` at review time.

### Automated status transitions
`bookings/management/commands/run_transitions.py`

- Approved → In Progress: `period_from <= today`
- In Progress → Completed: `period_to < today`

Designed to run daily via OS cron. The `CRONJOBS` entry in `settings.py` registers it at 01:00 server time; activate with `python manage.py crontab add` on the Linux server.

### Email notifications
`bookings/views.py: _send_new_request_email(transport_request)`

Called after every successful request save (both initial submission and post-nudge acknowledgment). Guards on `Settings.email_notifications_enabled` and a non-empty `Settings.notification_email`. Uses `fail_silently=True` so a broken SMTP configuration never prevents a request from being submitted. The backend is fully controlled by the `EMAIL_BACKEND` environment variable.

---

## Environment Variables

Commit a `.env.example` file to the repository; gitignore `.env`. The application reads all configuration from the `.env` file via `django-environ`.

```ini
# Core
DEBUG=True
SECRET_KEY=replace-with-a-50-char-random-string
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (use console backend locally; configure SMTP for production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=fleet@znphi.gov.zm
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@znphi.gov.zm

DJANGO_LOG_LEVEL=INFO
```

---

## Local Setup (Windows / PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env with local database credentials

python manage.py migrate

# Load province and district reference data
python manage.py loaddata bookings/fixtures/provinces_districts.json

# Create the 4 auth groups
python manage.py shell -c "
from django.contrib.auth.models import Group
for g in ['Requester', 'Fleet Manager', 'Dashboard Viewer', 'Superadmin']:
    Group.objects.get_or_create(name=g)
"

python manage.py createsuperuser

# Optional: load synthetic demo data
python manage.py seed_data

python manage.py runserver
```

---

## URL Reference

```
/                                          Home — redirects by role
/admin/                                    Django admin
/accounts/login/                           Login
/accounts/logout/                          Logout (POST)
/accounts/users/                           User list (Superadmin)
/accounts/users/create/                    Create user
/accounts/users/<pk>/group/               Assign role

/bookings/queue/                           Request queue (Fleet Manager, Superadmin)
/bookings/my-requests/                     My requests (all roles)
/bookings/new/                             New request form (all roles)
/bookings/nudge/                           Coordination nudge acknowledgment
/bookings/<pk>/                            Request detail
/bookings/<pk>/cancel/                     Cancel request (POST)
/bookings/<pk>/review/                     Review and assign (Fleet Manager, Superadmin)
/bookings/htmx/districts/                  HTMX endpoint — district dropdown

/fleet/vehicles/                           Vehicle list
/fleet/vehicles/add/                       Add vehicle (Fleet Manager, Superadmin)
/fleet/vehicles/<pk>/                      Vehicle detail
/fleet/vehicles/<pk>/edit/                 Edit vehicle
/fleet/vehicles/<pk>/fuel/add/             Log fuel record
/fleet/vehicles/<pk>/fuel/export/          CSV export — fuel log
/fleet/vehicles/<pk>/maintenance/add/      Log maintenance record
/fleet/vehicles/<pk>/maintenance/export/   CSV export — maintenance history
/fleet/drivers/                            Driver list
/fleet/drivers/add/                        Add driver (Fleet Manager, Superadmin)
/fleet/drivers/<pk>/edit/                  Edit driver

/dashboard/                                KPI dashboard
/dashboard/gantt/                          Gantt chart
/dashboard/district-data/                  JSON — district trip counts (Leaflet map)

/settings/                                 System settings (Fleet Manager, Superadmin)
```

---

## Tests and CI

```powershell
python manage.py test --verbosity=2
```

229 tests across all 5 apps. GitHub Actions (`.github/workflows/tests.yml`) runs the full suite on every push and pull request to `main`, using a Postgres 14 service container and Python 3.13.

---

## Management Commands

| Command | Purpose |
|---|---|
| `python manage.py seed_data` | Populate database with synthetic prototype data |
| `python manage.py flush_seed --no-input` | Remove all synthetic data; reference tables and real user accounts are preserved |
| `python manage.py run_transitions` | Advance statuses based on trip dates (normally run by cron) |
| `python manage.py crontab add` | Register `run_transitions` in OS cron at 01:00 (Linux only) |
| `python manage.py crontab remove` | Deregister the cron entry |
| `python manage.py collectstatic` | Collect static files to `staticfiles/` for production serving |

---

## Django Admin (`/admin/`)

Registered models: `Vehicle`, `Driver`, `FuelRecord`, `MaintenanceRecord`, `TransportRequest`, `TripAssignment`, `Province`, `District`, `Department`, `Settings`, `User`.

The `Settings` admin prevents creating a second row or deleting the existing one — it is always a singleton at `pk=1`.

Use admin for bulk corrections, adding new `Department` entries, editing reference data (provinces/districts), or inspecting raw records. Day-to-day operations belong in the main application UI.

---

## Integration into the Implementation Tracker

The implementation tracker and this fleet tool share the same stack (Django + PostgreSQL), making integration straightforward.

### Merging the apps

Copy the five Django apps (`accounts`, `bookings`, `fleet`, `dashboard`, `settings_app`) into the tracker project. Add them to `INSTALLED_APPS` and include their URL patterns in the tracker's root `urls.py`. Running `python manage.py migrate` creates the fleet tables in the shared database without touching existing tracker tables.

```python
# tracker/urls.py — add alongside existing patterns
path('fleet/', include('fleet.urls')),
path('bookings/', include('bookings.urls')),
path('dashboard/', include('dashboard.urls')),
path('settings/', include('settings_app.urls')),
```

### Context processors

Add both processors to the tracker's `TEMPLATES` configuration:

```python
'accounts.context_processors.user_roles',
'bookings.context_processors.pending_request_count',
```

These inject the role flags (`is_fleet_manager`, etc.) and the pending request badge count into every template context. The fleet templates depend on them.

### Navigation

Replace the fleet app's `base.html` navbar with the tracker's base template. The role flags are injected by the context processor and will be available in any template that extends the tracker's base once the processor is wired in.

### Email

Set the `EMAIL_*` environment variables once in the shared `.env`. Both applications will use the same backend; no code changes are required on the fleet side.

### Activity linkage

The natural integration point is `TransportRequest`. Add a field (FK or ID field) linking a transport request to the relevant tracker activity, expose it in the booking form, and surface transport request status on the activity detail page via a queryset join. The design of this relationship depends on the tracker's data model and is left to the IT team.

### Auth groups

The four fleet groups (`Requester`, `Fleet Manager`, `Dashboard Viewer`, `Superadmin`) must exist in the shared database. Create them via a data migration or the admin panel on first deploy. They can be mapped onto existing tracker roles or kept separate — the fleet app checks group membership by name only.

### Cron and static files (Docker / Proxmox)

After deploying the integration branch:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py crontab add   # registers run_transitions at 01:00
```

`django-crontab` writes to the OS cron daemon and is Linux-only. On Windows development machines, call `run_transitions` manually or via Windows Task Scheduler.
