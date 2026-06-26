# ZNPHI Fleet Management Tool — Construction Guide

**Partner:** ZNPHI Delivery Unit
**ZEL team:** Matteo Larrode, Stephen Jackson
**ZNPHI contacts:** Bridget Lumbwe (Head of Delivery Unit), Monze Mwanang'andu (Fleet Manager), Gideon Nyambe (M&E)
**Date:** June 2026

---

## Purpose of this document

This construction guide captures every architectural, design, and workflow decision made before entering Claude Code. It serves two purposes: (1) a complete brief for building the fleet management tool, and (2) a reviewable document for colleagues and stakeholders.

The tool replaces a paper-based transport requisition system at ZNPHI, which currently manages 23 vehicles with a 4-person admin team handling up to 60 requests per week. The system has no shared view of vehicle availability, no coordination across departments, and no maintenance tracking.

**What we are building:** A single web application with two integrated components — a booking system (all staff submit transport requests, the Fleet Manager approves and assigns) and a fleet dashboard (leadership monitors utilization, maintenance, and costs). The tool runs on synthetic data through June, with real data integration after the MoU is signed in July.

---

## 1. Tech Stack and Architecture

### Stack summary

| Layer | Choice | Rationale |
|---|---|---|
| Backend framework | Django | Python-native, batteries-included (auth, ORM, admin panel, forms). One language for the entire backend. Maintainable after handover by non-specialist developers. |
| Interactivity | HTMX | Dynamic UI behavior (live updates, form submissions without page reloads, filtering) via HTML attributes — no JavaScript framework required. Everything stays server-side in Python. |
| CSS framework | Tailwind CSS + DaisyUI | Tailwind provides utility classes for layout; DaisyUI adds pre-built components (buttons, cards, tables, modals, badges). Supports custom theming with ZNPHI colors. |
| Charts | Chart.js | Lightweight charting library for dashboard visualizations. Embedded in Django templates. |
| Maps | Leaflet.js | Open-source mapping library. Works with OpenStreetMap tiles (no API key needed). Used for the choropleth map. |
| Database | PostgreSQL | Robust, free, production-ready. Handles all relational data needs. |
| Template engine | Django templates | Default Django templating. No additional tooling. |

### Architecture decisions

**One application, role-based views.** The booking system and dashboard are not separate apps — they are different views within a single Django project, with access controlled by user role. This simplifies deployment, authentication, and data sharing.

**Authentication is swappable.** The prototype uses Django's built-in auth (username/password, group-based roles). The auth backend is structured so it can be replaced later with whatever the SPIM platform uses (LDAP, OAuth2, shared sessions) without changing application logic.

**URL prefix support.** The app is configurable to run at a subpath (e.g., `/fleet/`) rather than at the root domain, so it can sit alongside the SPIM platform in the future.

**Environment-based configuration.** All settings (database credentials, secret key, debug mode, allowed hosts, email config) are read from environment variables. Nothing is hardcoded. A `.env` file is used locally; real environment variables in production.

**No Docker for now.** Development happens directly in a Python virtual environment on Windows. The app is structured so a `Dockerfile` and `docker-compose.yml` can be added later if ZNPHI's IT team prefers containerized deployment.

**Production deployment (pending IT answers).** In production, the app will run behind Gunicorn (Python WSGI server) + Nginx (reverse proxy handling HTTPS and static files). Specifics depend on the server environment — see the separate IT questions document.

---

## 2. Users and Access

Four roles within a single application. Django's group-based permission system controls what each role can see and do.

### Requester

**Who:** Any ZNPHI staff member (~100–300 people).

**Can do:** Submit transport requests. View the status of their own requests. Cancel their own pre-completion requests.

**Authentication:** For the prototype, Django built-in auth. Eventually inherits credentials from the existing ZNPHI platform. People can submit requests on behalf of others (the "requester name" field is not auto-linked to the logged-in account).

### Fleet Manager

**Who:** Monze Mwanang'andu (initially; role is transferable).

**Can do:** Everything a Requester can do, plus: review and approve/reject requests, assign vehicles and drivers, manage the vehicle registry (add/edit vehicles, update mileage, log fuel and maintenance records), manage the driver list, schedule vehicles for maintenance, configure system settings (email notifications, buffer days, nudge time window, maintenance intervals). Access the Gantt chart and all operational views.

### Dashboard Viewer

**Who:** Bridget Lumbwe, Gideon Nyambe, the Director General, and potentially other leadership.

**Can do:** View the KPI dashboard (with time interval filtering), view the choropleth map, view the Gantt chart (read-only, no assignment actions). Cannot modify any data.

### Superadmin

**Who:** Matteo (during prototyping), then transferred to Monze or Bridget.

**Can do:** Manage user accounts, assign and transfer roles, access Django admin panel, configure system-level settings.

**Role transfers:** Reassigning a role (e.g., Fleet Manager moves from Monze to someone else) is done by moving a user between Django groups. A simplified admin screen should be built for this, so the person doing the transfer doesn't need the full Django admin panel.

### Drivers

Drivers are **not system users**. They exist as data entities (Monze assigns them to trips) but do not log in or interact with the application. This may change in the future.

---

## 3. Data Model

Seven entities. All managed through Django's ORM, backed by PostgreSQL.

### Vehicle

| Field | Type | Notes |
|---|---|---|
| make | string | e.g., Toyota |
| model | string | e.g., Hilux, Land Cruiser |
| year | integer | e.g., 2019 |
| license_plate | string | Unique. Zambian format. |
| vehicle_type | choice | Hilux / Land Cruiser |
| current_mileage | integer | In km. Manually updated by Monze (until GPS integration). |
| seating_capacity | integer | Total passenger capacity. Used for coordination nudging (spaces available). |
| fuel_type | choice | Diesel / Petrol |
| status | choice | Available / On Trip / In Maintenance / Emergency Standby |
| maintenance_interval_km | integer | Default 5,000. Editable by Monze per vehicle. |
| last_service_date | date | From most recent MaintenanceRecord. |
| last_service_mileage | integer | From most recent MaintenanceRecord. |
| created_at | datetime | Auto-set. |
| updated_at | datetime | Auto-set. |

**Relationships:** Has many TripAssignments, FuelRecords, MaintenanceRecords.

**Status logic:** "On Trip" is set automatically when a linked TripAssignment's request is in progress. "In Maintenance" is set manually by Monze (scheduled maintenance) or automatically when mileage exceeds threshold. "Emergency Standby" is a manual designation for the 3 reserve vehicles.

### Driver

| Field | Type | Notes |
|---|---|---|
| name | string | For the prototype: "Driver 1" through "Driver 20". |
| phone | string | Optional. |
| status | choice | Available / On Assignment / On Leave |
| created_at | datetime | Auto-set. |
| updated_at | datetime | Auto-set. |

**Relationships:** Has many TripAssignments.

**Note:** The relationship between drivers and vehicles is fluid — Monze assigns any available driver to any vehicle per trip. This assumption should be confirmed with Monze.

### Department

| Field | Type | Notes |
|---|---|---|
| name | string | Unique. |

**Departments for prototype:**
- Surveillance and Disease Intelligence
- Emergency Preparedness and Response
- National Public Health Laboratory Services (NPHLS)
- Public Health Policy, Diplomacy and Communication
- Field Epidemiology Program
- Public Health Security System Strengthening

### TransportRequest

| Field | Type | Notes |
|---|---|---|
| requester_name | string | Free text. Not auto-linked to logged-in user (people submit on behalf of others). |
| department | FK → Department | Dropdown. |
| position | string | Requester's position/title. |
| programme_activity | string | Name of programme or activity (purpose of the trip). |
| date_of_request | date | Auto-set to submission date. |
| period_from | date | Start of assignment period. |
| period_to | date | End of assignment period. |
| province | choice | Dropdown. 10 Zambian provinces. |
| district | choice | Cascading dropdown filtered by selected province. 116 districts. |
| destination | string | Free text. More specific location beyond district. |
| num_vehicles | integer | Number of vehicles required. |
| num_drivers | integer | Number of drivers required. |
| num_passengers | integer | Total passengers traveling. Used for coordination nudging (spaces calculation). |
| is_emergency | boolean | Emergency flag. Default false. |
| status | choice | Submitted / Approved / Rejected / In Progress / Completed / Cancelled |
| admin_comment | text | Monze's comment (on approval or rejection). |
| coordination_acknowledged | boolean | Whether requester acknowledged the coordination nudge. |
| coordination_note | text | Optional note from requester explaining why they still need a separate vehicle. |
| approved_date | date | Nullable. Set when Monze approves/rejects. |
| created_at | datetime | Auto-set. |
| updated_at | datetime | Auto-set. |

**Relationships:** Belongs to Department. Has many TripAssignments.

**Status transitions (partially automated):**
- **Submitted → Approved:** Monze assigns vehicles/drivers, adds comment, approves.
- **Submitted → Rejected:** Monze adds comment, rejects.
- **Approved → In Progress:** Automatic. Background task runs daily; when current date ≥ `period_from`, status transitions.
- **In Progress → Completed:** Automatic. When current date > `period_to`, status transitions.
- **Any pre-completion state → Cancelled:** Manual, by requester or Monze.

### TripAssignment

| Field | Type | Notes |
|---|---|---|
| transport_request | FK → TransportRequest | |
| vehicle | FK → Vehicle | |
| driver | FK → Driver | |

**Purpose:** Linking table. Each row connects one request to one vehicle and one driver. If a request needs 3 vehicles, there are 3 TripAssignment rows pointing to the same request.

### FuelRecord

| Field | Type | Notes |
|---|---|---|
| vehicle | FK → Vehicle | |
| date | date | |
| liters | decimal | |
| cost_per_liter | decimal | |
| total_cost | decimal | |
| location | string | Where the fill-up happened. |
| mileage_at_fillup | integer | Odometer reading at fill-up. |
| notes | text | Optional. |
| created_at | datetime | Auto-set. |

### MaintenanceRecord

| Field | Type | Notes |
|---|---|---|
| vehicle | FK → Vehicle | |
| date | date | |
| mileage_at_service | integer | Odometer reading at time of service. |
| service_type | string | e.g., Oil change, Full service, Tire rotation. |
| cost | decimal | |
| vendor | string | Service provider. |
| notes | text | Optional. |
| created_at | datetime | Auto-set. |

**Logic:** When a new MaintenanceRecord is created, the Vehicle's `last_service_date` and `last_service_mileage` are updated automatically (via Django signal or model save override).

### Reference data (not a model, loaded as fixtures)

**Provinces and districts:** 10 provinces, 116 districts. Pulled from the most recent official Zambian administrative boundaries. Used in cascading dropdowns on the request form and for district-level matching in coordination nudging.

---

## 4. Core Workflows

### 4.1 Booking workflow

**Step-by-step:**

1. Requester opens the booking form and fills in all fields (requester name, department, position, programme/activity, period from/to, province, district, destination, number of vehicles, number of drivers, number of passengers, emergency flag).

2. On submission, the system checks for existing trips to the same district within the configured time window (default: 7-day window).

3. **If overlap found →** A highlighted message appears: *"A vehicle with X spaces left is going to [district] from [date] to [date], booked by [name, department]. Consider reaching out to coordinate."* The requester must actively acknowledge this to proceed. They can optionally leave a note explaining why they still need a separate vehicle.

4. Request is saved with status **Submitted**.

5. Monze's dashboard shows an updated pending request count (badge).

6. If email notifications are enabled, Monze receives an email. The notification email address is configurable (to support role transfers).

7. Monze opens the request and sees: all request details; the coordination nudge (if applicable) with the requester's note; and a list of available vehicles for the requested dates.

8. The available vehicles list is filtered by date availability, respects a 1-day buffer between trips (configurable by Monze), and excludes vehicles that are overdue for maintenance. Each vehicle in the list shows key info on hover/click: returns from [district, province] on [date], last maintenance date, next maintenance due at [X km].

9. Monze selects vehicle(s) and driver(s), writes a comment, and approves or rejects.

10. Request status updates to **Approved** or **Rejected**.

11. Requester sees updated status in-app. (Email notification capability is built but inactive by default; can be enabled later.)

12. When current date ≥ `period_from` → status auto-transitions to **In Progress**.

13. When current date > `period_to` → status auto-transitions to **Completed**.

14. At any pre-completion stage, the requester or Monze can **Cancel**.

**Late booking warning:** If the request is submitted less than 2 weeks before the assignment start date, a warning is shown to the requester (but submission is not blocked). Late requests are tracked as a KPI on the dashboard.

**Buffer between trips:** A 1-day default buffer between consecutive bookings for the same vehicle. Configurable by Monze in system settings.

### 4.2 Maintenance workflow

1. Each vehicle has a configurable maintenance interval (default 5,000 km) and a baseline from its most recent MaintenanceRecord (`last_service_mileage`).

2. Monze manually updates vehicle mileage periodically. (The system is designed so trip-completion mileage entry can be added later when mileage tracking improves.)

3. The dashboard shows a per-vehicle maintenance indicator:
   - **Green:** More than 500 km to next service.
   - **Amber:** 500 km or less to next service.
   - **Red:** Overdue (current mileage ≥ last service mileage + maintenance interval).

4. **Overdue vehicles are blocked from assignment.** They do not appear in Monze's available vehicle list when reviewing requests.

5. Monze can **manually schedule a vehicle for maintenance**, marking it unavailable for a specific date range. This blocks it from assignment during that window.

6. When maintenance is performed, Monze creates a MaintenanceRecord (date, mileage, service type, cost, vendor, notes).

7. Creating the record **resets the maintenance baseline** and returns the vehicle to available status.

### 4.3 Coordination nudging

**Purpose:** Flag when multiple vehicles are heading to the same area in the same timeframe, enabling coordination or carpooling.

**Matching criteria:** Same district (reliable matching thanks to the dropdown; no free-text ambiguity).

**Time window (configurable by Monze in settings):**
- Exact date overlap only
- Within the same 7-day window (default)
- +/- X days, where X is configurable

**Trigger point 1 — at submission:** The requester sees a highlighted message with details of overlapping trips (destination, dates, requester name/department, spaces left on the vehicle). They must acknowledge the nudge to proceed and can leave an optional note.

**Trigger point 2 — at approval:** Monze sees the same overlapping trip information plus the requester's note. The nudge encourages Monze to contact the requester to explore coordination. The options remain approve or reject — the nudge is informational, never blocking.

**Spaces calculation:** Vehicle seating capacity minus number of passengers on the existing trip equals spaces available.

---

## 5. Views and Pages

### Requester screens

**New Request Form**
- All TransportRequest fields as form inputs.
- Province/district as cascading dropdowns.
- Emergency flag as a toggle.
- On submit: coordination nudge (if applicable) with acknowledgment and optional note.
- Late booking warning if submission is less than 2 weeks before assignment start.

**My Requests**
- List of all requests submitted by the logged-in user.
- Columns: date of request, programme/activity, district, period, status (color-coded badge), assigned vehicle(s).
- Click into a request to see full detail including Monze's comment.
- Cancel button on pre-completion requests.

### Fleet Manager screens

**Request Queue** (landing page)
- List of all **Submitted** requests, sorted by urgency: emergency-flagged first, then by assignment start date (soonest first).
- Pending request count as a badge in the top navbar.
- Each row shows: requester name, department, dates, district, number of vehicles, emergency flag.
- Click into a request to open the review screen.

**Request Review and Assignment**
- Full request details displayed.
- Coordination nudge panel (if overlapping trips exist) with the requester's note.
- Available vehicles panel: list of vehicles available for the requested dates, filtered by buffer rules, excluding overdue-maintenance vehicles. Each vehicle shows on hover/click: where it's returning from and when, last maintenance date, next maintenance due at [X km].
- Assignment controls: select vehicle(s) and driver(s), write a comment.
- Approve / Reject buttons.

**Gantt Chart**
- Rows: all 23 vehicles.
- Columns: time (days/weeks).
- Bookings shown as colored blocks, labeled with destination district.
- Province filter: filter the view to show only trips going to a selected province.
- Shared with Dashboard Viewers (read-only for them, interactive assignment context for Monze).

**Vehicles & Maintenance**
- Vehicle registry table: make, model, plate, current mileage, status, maintenance traffic light (green/amber/red).
- Click into a vehicle to see/edit: vehicle details, current mileage input, fuel log (list of FuelRecords with ability to add new), maintenance history (list of MaintenanceRecords with ability to add new), upcoming bookings, schedule maintenance (set a date range to block the vehicle).
- Driver registry as a sub-section or tab: list of all drivers, status, ability to edit details and change availability.

**Settings**
- Email notifications: on/off toggle, email address field.
- Buffer days between trips: integer input (default 1).
- Coordination nudge time window: mode selection (exact overlap / 7-day window / +/- X days) with X input.
- Default maintenance interval for new vehicles: integer input in km (default 5,000).

### Dashboard Viewer screens

**KPI Dashboard**
- Time interval selector (slider or date range picker) — can be set to one month or any custom range.
- KPI panels:
  - **Fleet utilization:** % of vehicle-days used vs available, most/least used vehicles.
  - **Request volume:** total requests, approved vs rejected count, average lead time (how far in advance people book), percentage of late requests (under 2 weeks).
  - **Maintenance health:** count of green/amber/red vehicles now, maintenance costs over the selected period, upcoming services.
  - **Trip patterns:** trips by department, most common destination districts.
  - **Finance:** total fuel costs, total maintenance costs, cost per vehicle, cost per trip, projected maintenance costs for upcoming months (based on current mileage rates and service intervals).

**Choropleth Map**
- Zambia map colored by district, showing trip density (number of trips per district) over the selected time interval.
- Month toggle to view seasonality patterns.
- Built with Leaflet.js using Zambian district boundary shapefiles.

**Gantt Chart** (read-only)
- Same view as the Fleet Manager's Gantt chart, without assignment actions.

### Superadmin

- Django's built-in admin panel for user management, role assignment, and system configuration during the prototype phase.
- A simplified admin screen for role transfers is a future deliverable for handover.

### Shared components

- **Top navbar:** Present on all screens. Shows the app name/logo, navigation links (role-dependent), logged-in user name and role, and the pending request badge (for Monze).
- **CSV export buttons:** On key list views (requests, vehicles, fuel records, maintenance records) for Excel-friendly data export.

---

## 6. Visual Design

### Color palette

| Color | Hex | Role |
|---|---|---|
| Dark blue | `#3A405A` | **Primary.** Buttons, links, active states, selected items, navbar background. |
| Light blue | `#B5CCE2` | Primary hover/light variant, info badges, secondary highlights. |
| Red | `#D71116` | Error, rejected status, overdue maintenance (red indicator), emergency flag badge, destructive actions (cancel). |
| Green | `#228843` | Success, approved status, healthy maintenance (green indicator), completed status. |
| Orange | `#EA802B` | Warning, submitted/pending status, approaching maintenance (amber indicator), late booking warning, coordination nudge highlight. |
| Light mint | `#eef7f2` | Page background, card fills. |
| Light grey | `#e4e3e1` | Borders, table row alternation, dividers, disabled states. |
| Dark charcoal | `#3e3b38` | Primary text, headings. |

These map to a custom DaisyUI theme:
- `primary` → `#3A405A`
- `secondary` → `#B5CCE2`
- `accent` → `#EA802B`
- `neutral` → `#3e3b38`
- `base-100` → `#eef7f2`
- `success` → `#228843`
- `warning` → `#EA802B`
- `error` → `#D71116`

### Typography

**Font:** Inter. Bundled with the application (served from static files, not loaded from an external CDN). This avoids dependency on internet connectivity.

### Navigation

Top navbar across all roles. Role determines which nav items are visible:
- **Requester:** New Request, My Requests.
- **Fleet Manager:** Request Queue, Gantt Chart, Vehicles & Maintenance, Dashboard, Settings.
- **Dashboard Viewer:** Dashboard, Map, Gantt Chart.
- **Superadmin:** Admin panel link.

The navbar shows the logged-in user's name and role, and displays the pending request badge for the Fleet Manager.

### Density and spacing

Relaxed spacing throughout. Enough whitespace to keep data-heavy screens (request queue, vehicle registry, Gantt chart) scannable without overwhelming the user. Comfortable for all-day use on a laptop. Not overly sparse — the goal is clean and efficient, not magazine-style.

### Responsive behavior

- **Minimum width:** 768px (tablet portrait).
- **Optimized for:** 1200px+ (laptop).
- Horizontal scrolling is acceptable for the Gantt chart on tablet-width screens.
- No phone optimization in the prototype. Users are expected to access the tool primarily on laptops.

---

## 7. Synthetic Data

The prototype runs on synthetic data through June. Real data integration begins after the MoU is signed in July.

### Approach

A Django management command (`python manage.py seed_data`) generates all synthetic data programmatically through the ORM, populating the real PostgreSQL database with the real schema. A corresponding `python manage.py flush_seed` clears synthetic data before real data is loaded.

The management command is preferred over static fixtures because the data has internal logic: requests reference specific vehicles and drivers, maintenance records align with mileage, and coordination nudge clusters are intentionally placed.

### Volumes and characteristics

| Entity | Volume | Characteristics |
|---|---|---|
| Vehicles | 23 | ~12 Hiluxes, ~11 Land Cruisers. 3 designated emergency standby. Years ranging 2016–2023. Current mileage spread 30,000–180,000 km. A few vehicles in the amber zone (approaching maintenance), 1–2 in the red zone (overdue). |
| Drivers | 20 | Named "Driver 1" through "Driver 20". Most available, a couple on leave. |
| Departments | 6 | The six ZNPHI departments (see Section 3). |
| Provinces & districts | 10 + 116 | Real Zambian administrative data. Loaded as reference fixtures. |
| Transport requests | ~250–300 | 3–4 months of history (approx. March–June 2026). Baseline ~20 requests/week, with one spike week at ~60. Mixed statuses: most completed, some approved/in progress, a batch of submitted (pending in Monze's queue for demo). A handful rejected with comments. Some emergency-flagged. Some submitted less than 2 weeks before assignment (late requests). Intentional clusters of trips to the same district in the same week to trigger coordination nudges during demos. |
| Trip assignments | Matching requests | Most requests have 1 vehicle assigned. Some have 2–3 (demonstrating multi-vehicle). |
| Fuel records | ~3 months per vehicle | Realistic Zambian fuel prices. Vehicles used more often have more records. Varied fill-up locations. |
| Maintenance records | History per vehicle | Past services spaced roughly every 5,000 km. Combined with current mileage, this creates the green/amber/red spread across the fleet. |

---

## 8. Deployment and Integration

### Local development environment

- **OS:** Windows.
- **Python:** 3.11+ in a virtual environment.
- **Database:** PostgreSQL running locally.
- **Server:** Django's built-in development server (`manage.py runserver`).
- **Setup goal:** Clone repo → create venv → install from `requirements.txt` → set `.env` → run migrations → load seed data → start server. Documented in `README.md`.

### Production deployment (pending IT answers)

- **Target:** Gunicorn (WSGI server) behind Nginx (reverse proxy, HTTPS, static files).
- **Configuration:** Environment variables for all settings.
- **Docker:** Not used initially. App structured so `Dockerfile` + `docker-compose.yml` can be added later.
- **Details depend on ZNPHI server environment** — see the separate IT questions document.

### Integration with SPIM platform

- **Current state:** Fully decoupled. The fleet tool is a standalone Django application.
- **Path to integration:**
  - **Authentication:** Django built-in auth for now, structured so the backend can be swapped for the SPIM platform's auth method (LDAP, OAuth2, shared sessions) without changing application logic.
  - **URL structure:** App is configurable to run at a subpath (e.g., `/fleet/`).
  - **Lightest integration:** A link in the SPIM platform's navigation that opens the fleet tool. Requires no code changes to either system.
  - **Deeper integration:** Shared authentication (single sign-on). Requires understanding the SPIM platform's auth approach.
  - **Specifics depend on IT answers.**

### Future GPS/Traccar integration

- Not built in the prototype.
- When GPS trackers are deployed, Traccar (open-source, self-hosted GPS tracking) can feed live mileage data into the fleet tool via its REST API.
- The integration point: a scheduled task pulls current mileage per vehicle from Traccar and updates the Vehicle record in Django. This replaces manual mileage entry and makes maintenance alerts automatic.
- No architectural changes needed — the Vehicle model already has `current_mileage` and the maintenance logic already uses it.

### Data export

CSV export buttons on key list views: transport requests, vehicle registry, fuel records, maintenance records. Low effort, high value for a team transitioning from Excel.

### Code quality and maintainability

The codebase must be maintainable by someone other than the original developer. This means:
- **Clear code comments** explaining the "why" behind non-obvious logic (especially workflow automation, nudging criteria, and maintenance calculations).
- **Modular structure:** Django apps organized by domain (e.g., `bookings`, `fleet`, `dashboard`) rather than one monolithic app.
- **Clear naming conventions** for models, views, URLs, and templates.
- **README.md** with full setup instructions.
- **Admin guide** (deliverable produced later with screenshots): how to add a vehicle, change a user's role, reset a password, restart the app.

### Logging and backups

- **Logging:** Basic request and error logging configured from the start (Django's built-in logging framework).
- **Backups:** A `pg_dump` script for database backups. Specifics (frequency, storage location) depend on IT answers.