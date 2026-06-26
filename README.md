# ZNPHI Fleet Manager

Fleet management web application for the Zambia National Public Health Institute. Handles the full lifecycle of transport requests — submission, Fleet Manager review and vehicle/driver assignment, maintenance tracking, and a KPI dashboard with a Zambia district choropleth map.

![Tests](https://github.com/matteo-larrode/ZNPHI-Fleet-Manager/actions/workflows/tests.yml/badge.svg)

## Features

- **Transport requests** — multi-step booking form with province → district cascading dropdown (HTMX), late-booking warning, and a coordination nudge that surfaces overlapping trips to the same district
- **Fleet Manager workflow** — request queue, vehicle/driver availability filtering (with configurable buffer days), approval/rejection with comments
- **Maintenance tracking** — per-vehicle maintenance log with traffic-light health indicators (green / amber / red) that block overdue vehicles from assignment
- **Fuel records** — per-vehicle fuel log with CSV export
- **Gantt chart** — vehicle bookings over time, filterable by province
- **KPI dashboard** — fleet utilisation, request volume, maintenance health, trip patterns by department and district, financial summary; choropleth map via Leaflet.js
- **Role-based access** — four roles (Requester, Fleet Manager, Dashboard Viewer, Superadmin), enforced at the view level
- **Automated status transitions** — daily management command advances request and vehicle/driver statuses by date
- **Email notifications** — configurable SMTP notifications on new request submission
- **CSV exports** — fuel logs and maintenance history per vehicle

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5, Python 3.11+ |
| Database | PostgreSQL 14+ |
| Interactivity | HTMX |
| CSS | Tailwind CSS + DaisyUI |
| Charts | Chart.js |
| Maps | Leaflet.js + OCHA district GeoJSON |
| Config | django-environ |
| Scheduled tasks | django-crontab (Linux only) |

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- District boundary GeoJSON files (see below)

## District boundary data

The choropleth map requires district-level boundary files that are not included in the repository due to size. Source them from [OCHA Humanitarian Data Exchange](https://data.humdata.org/dataset/cod-ab-zmb) (Zambia COD-AB dataset), convert to GeoJSON, and place in `geo_data/` before running the application.

## Local setup

**Windows (PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env with your database credentials and secret key

python manage.py migrate
python manage.py loaddata bookings/fixtures/provinces_districts.json

python manage.py shell -c "
from django.contrib.auth.models import Group
for g in ['Requester', 'Fleet Manager', 'Dashboard Viewer', 'Superadmin']:
    Group.objects.get_or_create(name=g)
"

python manage.py createsuperuser
python manage.py seed_data   # optional: load synthetic demo data
python manage.py runserver
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your database credentials and secret key

python manage.py migrate
python manage.py loaddata bookings/fixtures/provinces_districts.json

python manage.py shell -c "
from django.contrib.auth.models import Group
for g in ['Requester', 'Fleet Manager', 'Dashboard Viewer', 'Superadmin']:
    Group.objects.get_or_create(name=g)
"

python manage.py createsuperuser
python manage.py seed_data   # optional: load synthetic demo data
python manage.py runserver
```

## Running tests

```bash
python manage.py test --verbosity=2
```

229 tests. CI runs automatically on push and pull requests to `main` via GitHub Actions.

## Scheduled tasks

`python manage.py run_transitions` advances request statuses (Approved → In Progress → Completed) and re-syncs vehicle/driver operational statuses by date. It is designed to run daily.

On Linux/macOS, register it with the OS cron daemon:

```bash
python manage.py crontab add    # schedules at 01:00 daily
python manage.py crontab remove # deregisters
```

`django-crontab` is Linux/Unix only. On Windows, use Windows Task Scheduler or run the command manually.

## Seed data

`python manage.py seed_data` populates the database with synthetic prototype data (23 vehicles, 20 drivers, 334 requests). Clear it with `python manage.py flush_seed --no-input`. Seed accounts are created without a usable password — set one via the admin panel before logging in as a seed user.

## Project structure

```
fleet_project/    Django project root — settings.py, urls.py, wsgi.py
accounts/         Auth, 4 role groups, GroupRequiredMixin, context processors
bookings/         Transport requests, trip assignments, provinces/districts
fleet/            Vehicles, drivers, fuel records, maintenance records
dashboard/        KPI dashboard, Gantt chart, choropleth map
settings_app/     Singleton Settings model — configurable thresholds and email
templates/        HTML templates (base.html + per-app subdirectories)
static/           Tailwind/DaisyUI CSS, Chart.js
geo_data/         District boundary GeoJSON — gitignored, source from OCHA
.github/          CI workflow
documentation/    Technical handover guide
```

## Documentation

See [documentation/HANDOVER.md](documentation/HANDOVER.md) for the full technical handover: data model reference, role matrix, core application logic, environment variables, URL map, and integration guide for merging into the ZNPHI implementation tracker.
