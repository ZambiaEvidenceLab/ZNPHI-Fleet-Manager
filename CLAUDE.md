# CLAUDE.md

## Project Overview

You are helping build a fleet management web application for ZNPHI (Zambia National Public Health Institute). The full specification is in `ZNPHI_Fleet_Tool_Construction_Guide.md` at the project root — read it before doing anything. That document is the source of truth for all architecture, data model, workflow, and design decisions.

## Development Approach

**Work iteratively.** Do not try to build the entire app in one pass. Each task should result in working, testable code that can be committed independently. After completing each task, stop and confirm with me before moving on.

**Typical cycle:**
1. I give you a task (or we agree on the next one from the phase plan below).
2. You implement it — models, views, templates, tests.
3. You run the tests to make sure they pass.
4. You show me what you've done and flag any decisions you made or questions that came up.
5. I review, we fix anything, and I commit.
6. Next task.

**Do not skip ahead.** If you're building Phase 2, don't start pulling in Phase 4 concerns. Keep each piece focused.

## Phase Plan

Build in this order. Each phase produces working, testable functionality.

### Phase 1: Project scaffold and data model
- Initialize Django project (`fleet_project`) and app structure (`bookings`, `fleet`, `dashboard`, `accounts`).
- Set up PostgreSQL connection via environment variables (`.env` with `django-environ`).
- Configure settings: installed apps, static files, templates directory.
- Define all 7 models (Vehicle, Driver, Department, TransportRequest, TripAssignment, FuelRecord, MaintenanceRecord) with fields exactly as specified in the construction guide.
- Create and run migrations.
- Register models in Django admin.
- Write model tests: field validation, relationships, string representations.
- Load reference data fixture: 10 provinces, 116 districts.

### Phase 2: Authentication and role-based access
- Set up Django's built-in auth with 4 groups: Requester, Fleet Manager, Dashboard Viewer, Superadmin.
- Create login/logout views and templates.
- Build middleware or decorators to restrict views by role.
- Create a simple user management page for Superadmin (list users, assign to groups).
- Write tests: login, role-based access control, group assignment.

### Phase 3: Booking form and request submission
- Build the transport request form with all fields.
- Implement cascading province → district dropdown (HTMX).
- Implement the late booking warning (< 2 weeks).
- Implement coordination nudge logic: query overlapping trips by district and time window, display highlighted message, require acknowledgment.
- Save request with status "Submitted."
- Build the "My Requests" list view for requesters (own requests only, status badges, click to detail, cancel action).
- Write tests: form validation, cascading dropdown, nudge trigger logic, request creation, cancellation.

### Phase 4: Fleet Manager approval and assignment workflow
- Build the request queue view (pending requests, sorted by urgency).
- Build the request review/assignment screen: request details, coordination nudge display, available vehicles list with hover info, vehicle and driver assignment, comment field, approve/reject.
- Implement availability filtering: exclude vehicles booked for overlapping dates (with buffer), exclude overdue-maintenance vehicles.
- On approval: create TripAssignment records, update request status.
- On rejection: update request status, save comment.
- Build the pending request badge count in the navbar.
- Write tests: availability filtering, buffer logic, assignment creation, status transitions.

### Phase 4.5: Seed data (pulled forward from Phase 9)
- Build the `seed_data` management command generating all synthetic data as specified in the construction guide.
- Build the `flush_seed` management command to clear synthetic data.
- Rationale: all 7 models exist; having realistic data from this point forward lets each subsequent phase be validated against a populated UI rather than empty screens. Statuses that depend on auto-transitions (Phase 8) are set directly in the seed command.
- UI polish, final test pass, and the "run full seed + test all views" sign-off remain in Phase 9.

### Phase 5: Vehicle and maintenance management
- Build the Vehicles & Maintenance list view (table with traffic lights).
- Build the vehicle detail view: edit vehicle info, update mileage, fuel log (list + add form), maintenance history (list + add form), upcoming bookings, schedule maintenance.
- Build the driver list view (sub-section or tab).
- Implement maintenance traffic light logic (green/amber/red based on mileage gap).
- Implement maintenance blocking (overdue vehicles excluded from assignment — connects to Phase 4 filtering).
- Implement MaintenanceRecord creation resetting the maintenance baseline.
- Write tests: traffic light calculation, maintenance blocking, record creation and baseline reset.

### Phase 6: Gantt chart
- Build the Gantt chart view: vehicles as rows, time as columns, bookings as blocks.
- Implement province filter.
- Make it accessible to both Fleet Manager (interactive context) and Dashboard Viewer (read-only).
- This involves some frontend JavaScript (rendering the chart). Use a lightweight library or build with plain HTML/CSS + HTMX where possible.
- Write tests: data query correctness, filtering.

### Phase 7: Dashboard and KPIs
- Build the KPI dashboard with time interval selector.
- Implement each KPI panel: fleet utilization, request volume, maintenance health, trip patterns by department, finance.
- Build the choropleth map (Leaflet.js + district boundary GeoJSON).
- Implement month toggle for seasonality view.
- Write tests: KPI calculation logic, date filtering.

### Phase 8: Settings, notifications, and automated tasks
- Build the Settings page (email config, buffer days, nudge time window, default maintenance interval).
- Implement email notification capability (Django email backend) — built but inactive by default.
- Implement the background task for automated status transitions (Submitted→In Progress→Completed based on dates). Use `django-crontab` or Celery beat depending on complexity.
- CSV export buttons on key list views.
- Write tests: settings persistence, status auto-transition logic, CSV export.

### Phase 9: Polish and final sign-off
- Run full seed, test all views with populated data.
- UI polish: consistent spacing, color application, navbar behavior across roles.
- Final test pass.
- Note: `seed_data` and `flush_seed` commands were built in Phase 4.5.

## Coding Standards

**Follow these strictly:**

- **Tests for everything.** Every model, every view, every piece of business logic gets a test. Use Django's `TestCase`. Run tests after every change.
- **Clear naming.** Models, views, URLs, and templates should be self-documenting. `TransportRequestCreateView`, not `CreateView1`. `vehicle_detail.html`, not `detail.html`.
- **Comments for the "why."** Don't comment obvious code. Do comment business logic: why a vehicle is excluded from the list, how the nudge time window works, what triggers a status transition.
- **Modular apps.** Keep Django apps focused: `bookings` handles requests and assignments, `fleet` handles vehicles/drivers/maintenance/fuel, `dashboard` handles KPIs and maps, `accounts` handles auth and user management.
- **DRY but readable.** Extract shared logic into utils or mixins, but don't over-abstract. A junior developer reading this codebase should be able to follow it.
- **No hardcoded values.** Settings, thresholds (maintenance interval, buffer days, nudge window), and configuration come from the database (Settings model) or environment variables. Never magic numbers in business logic.
- **Git-friendly changes.** Keep each piece of work small enough to be one meaningful commit. Don't mix unrelated changes.

## Tech Stack Reference

- **Backend:** Django 5.x, Python 3.11+
- **Database:** PostgreSQL 14+
- **Interactivity:** HTMX (django-htmx)
- **CSS:** Tailwind CSS + DaisyUI (custom ZNPHI theme)
- **Charts:** Chart.js
- **Maps:** Leaflet.js
- **Font:** Inter (bundled in static files)
- **Environment:** django-environ for `.env` configuration

## What to Do When Uncertain

- If the construction guide doesn't cover something, ask me before making an assumption.
- If you encounter a technical choice (e.g., which HTMX pattern to use, how to structure a complex query), explain the options briefly and recommend one. Don't just pick silently.
- If a test fails, diagnose it before moving on. Don't skip broken tests.