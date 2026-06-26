# ZNPHI Fleet Manager — Demo & Training Guide

**Audience:** ZNPHI stakeholders, fleet management staff, and system administrators  
**Application:** ZNPHI Fleet Manager — transport request and fleet management platform  
**Prepared by:** Matteo Larrode  

---

## Table of Contents

1. [Before the Demo](#1-before-the-demo)
2. [Demo Walkthrough](#2-demo-walkthrough)
3. [User Journey Narrative](#3-user-journey-narrative)
4. [Edge Cases to Demonstrate](#4-edge-cases-to-demonstrate)
5. [System Configuration — Settings Page](#5-system-configuration--settings-page)
6. [Adding to the System](#6-adding-to-the-system)
7. [Django Admin Panel Walkthrough](#7-django-admin-panel-walkthrough)
8. [Quick Reference Card](#8-quick-reference-card)

---

## 1. Before the Demo

### Environment checklist

- [ ] The application server is running and accessible at the demo URL
- [ ] The database is populated with seed data (23 vehicles, 20 drivers, 334 requests — see verification steps below)
- [ ] You have opened **four browser tabs** before the presentation begins (one per role — use separate private/incognito windows to hold multiple sessions simultaneously)
- [ ] Browser zoom is set to 100–110% so all text is readable on the projector
- [ ] No pending unsaved form data in any tab from a previous rehearsal
- [ ] The Django admin is accessible at `/admin/`

### Accounts to be logged in

| Tab | Account | Role | Password |
|---|---|---|---|
| Tab 1 | A requester (any `seed_*` account, e.g. `seed_grace`) | Requester | `fleetdemo2024` |
| Tab 2 | `fleet_manager` | Fleet Manager | `fleetdemo2024` |
| Tab 3 | `dashboard_viewer` | Dashboard Viewer | `fleetdemo2024` |
| Tab 4 | `superadmin` | Superadmin | `fleetdemo2024` |

*Tip: label each browser window with its role name by pinning the tab or using browser profiles. Switching between the wrong accounts mid-demo is the most common disruption.*

### Data verification (run before the audience arrives)

Log in as Fleet Manager and confirm:

- **Vehicles & Maintenance** page shows at least one red (overdue) vehicle — needed for the guardrails demo
- **Request Queue** shows at least one Submitted request — needed for the approval demo
- **KPI Dashboard** loads with charts and the choropleth map rendered (Leaflet tiles load from local static files; no internet required)
- **Gantt Chart** shows booking blocks across at least a few vehicles

If the database is empty or incomplete, run the seed command from the server:

```bash
python manage.py seed_data
```

To reset to a clean seed state:

```bash
python manage.py flush_seed
python manage.py seed_data
```

### Slides / narrative aid

Keep `ZNPHI_Fleet_Manager_Demo_Guide.md` (this file) open in a second window or on a secondary screen. The [User Journey Narrative](#3-user-journey-narrative) section gives you a storyline you can narrate aloud while clicking through the application.

---

## 2. Demo Walkthrough

Work through the roles in this order: **Requester → Fleet Manager → Dashboard Viewer → Superadmin**. The sequence follows a single request from submission to analytics, which makes the story coherent for the audience.

---

### 2.1 Requester flow

**Switch to Tab 1 (Requester account).**

#### Login page

- Navigate to the application root. You are redirected to the login page.
- Point out: "Every user logs in with a username and password. The system then shows only the features relevant to their role — a Requester sees a completely different navigation menu from a Fleet Manager."
- Log in as the Requester account.

#### New Transport Request form

- Click **New Request** in the navigation.
- Walk through the form fields top-to-bottom:
  - **Purpose of trip** — free text; reason the vehicle is needed
  - **Department** — the requesting department (Epidemiology, Labs, Finance, etc.)
  - **Number of passengers**
  - **Province → District** — *click the Province dropdown and select a province.* Point out: "Watch the District dropdown — it refreshes automatically, showing only districts that belong to that province. This uses a technology called HTMX, which updates just that part of the page without a full reload."
  - **Departure and return dates**
  - **Emergency checkbox** — "Emergency requests are flagged visually and sorted to the top of the Fleet Manager's queue."
  - **Additional notes**

#### Late booking warning

- Set the departure date to **within the next 14 days**.
- Point out the yellow banner that appears: "The system flags that this request has been submitted with fewer than 14 days' notice. This doesn't block submission — it's a courtesy alert so the Fleet Manager is aware."

#### Coordination nudge

- Set the Province and District to a destination that already has an existing trip in the seed data within the next seven days. (The district **Chipata** in **Eastern Province** typically works with the seed data.)
- As soon as you select the district, a highlighted warning panel appears: "Another trip is already planned to this district within a 7-day window."
- Point out the **acknowledgment checkbox** at the bottom of the nudge panel. "The requester cannot submit the form until they check this box. The system is nudging them to coordinate — perhaps share a vehicle, adjust their dates, or at minimum be aware of the other trip."
- Check the acknowledgment box. The Submit button becomes active.
- Submit the request.

#### My Requests

- Navigate to **My Requests**.
- Show the list: each row has the destination, travel dates, and a coloured **status badge** (Submitted, Approved, In Progress, etc.).
- Click through to one completed request in the seed data. Point out: "No cancel button here — the system only shows the Cancel button on requests that are still Submitted, Approved, or In Progress. Once a trip is done or rejected, there is nothing to cancel."
- Go back and find the request just submitted. The Cancel button is visible. You don't need to cancel it — just show its presence.

---

### 2.2 Fleet Manager flow

**Switch to Tab 2 (Fleet Manager account).**

#### Navigation and pending badge

- Point out the **badge count** on the Request Queue nav item. "This number updates live — every time a new request is submitted, it increments. Fleet Managers always know how much work is waiting."

#### Request Queue

- Navigate to **Request Queue**.
- Highlight: emergency requests appear at the top with a red **Emergency** badge and a highlighted row. "Sorting by urgency is automatic — emergencies rise to the top without manual intervention."
- Point out the **Export CSV** button. "The Fleet Manager can export this entire queue to a spreadsheet at any time."

#### Request Review & Assignment

- Click on the request submitted in the Requester demo (or any Submitted request).
- Walk through the page sections:
  1. **Request details panel** — who requested it, where, when, why
  2. **Coordination nudge panel** (if applicable) — same warning the requester saw, so the Fleet Manager knows about the overlap
  3. **Available vehicles** — "This list has already been filtered. Vehicles with overlapping bookings (accounting for a configurable buffer period) are excluded. Vehicles that are overdue for maintenance are also excluded and cannot be assigned."
  4. Hover over a vehicle row to see its quick-info tooltip (plate number, make/model, mileage, maintenance status).
  5. Select a vehicle. Select a driver. Optionally add a comment.
  6. Click **Approve**. "The system creates the assignment records, updates the request status to Approved, and the requester would receive a notification if email is configured."
- Go back and find a Submitted request to demonstrate rejection: click **Reject**, add a comment, submit. "The requester sees the rejection and the reason."

#### Vehicles & Maintenance

- Navigate to **Vehicles & Maintenance**.
- Point out the **maintenance traffic light** column:
  - **Green dot** — service not due, more than 500 km remaining
  - **Amber dot** — service due soon, within 500 km
  - **Pulsing red dot** — overdue. "This vehicle cannot be assigned to any new trip until it is serviced. If a Fleet Manager tries to assign it, it simply won't appear in the available vehicles list."
- Click through to a **vehicle detail page**:
  - Specs panel (make, model, year, plate, seating capacity)
  - Current mileage and maintenance status
  - **Fuel Log** section — show existing entries, then click **Add Fuel Record**. Fill in date, litres, cost, location, and mileage. Submit. "Every fuel fill is logged here, feeding the cost-per-km and total spend metrics on the dashboard."
  - **Maintenance History** section — show an existing record. Click **Add Maintenance Record**. "When a maintenance record is saved, the system automatically resets the service baseline — the mileage counter resets and the vehicle's status moves from 'In Maintenance' back to 'Available'. One action, three things updated."
  - **Upcoming bookings** panel — all future approved trips for this vehicle in one place.
  - Show the **Export CSV** buttons for both the fuel log and maintenance history.

#### Gantt Chart

- Navigate to **Gantt Chart**.
- Explain the layout: "Vehicles run down the left column. Time runs left to right. Each coloured block is an approved booking — you can see at a glance which vehicles are busy and which are free."
- Use the **Province filter** to narrow to a single province and show how the chart reduces to only vehicles with bookings in that province.

---

### 2.3 Dashboard Viewer flow

**Switch to Tab 3 (Dashboard Viewer account).**

#### Read-only access

- Navigate to the **KPI Dashboard**.
- Point out: "The Dashboard Viewer sees exactly the same charts and data as the Fleet Manager — but there are no action buttons anywhere. No assign, no approve, no add vehicle. This role is designed for leadership and ministry users who need visibility without the risk of accidentally modifying data."

#### KPI Dashboard

Walk through each panel using the **30-day** interval selector:

- **Fleet Utilisation** — "What percentage of our vehicle-days were actually in use during this period? The system also surfaces the most-utilised vehicle and the most idle one."
- **Request Volume** — "How many requests came in, how many were approved, how many rejected. Crucially, the average lead time — how far in advance staff are booking — and the late booking rate."
- **Maintenance Health** — "A snapshot of fleet condition right now: how many vehicles are green, amber, or red. Total maintenance spend for the period. Vehicles due for service within the next 1,000 km."
- **Finance** — "Total spend — fuel and maintenance combined — for the selected period. Cost per trip and cost per vehicle. Use the horizon selector to see projected maintenance costs over the next 1, 3, or 6 months."
- **Choropleth Map** — "Trip density across all 116 districts, visualised as a colour gradient on the map. Darker means more trips. Use the month buttons below the map to view individual months and see seasonal patterns — for instance, whether field activity spikes before or after the rainy season."
- **Requests by Department** bar chart — "Which department is making the most transport requests? Useful for budgeting and planning."
- **Top Destination Districts** list.

*Tip: hover over the choropleth map polygons — each district shows a tooltip with its name and exact trip count.*

- Click the **Export CSV** button. "This produces a single file with three sections — all transport requests, all fuel records, and all maintenance records for the selected period. Ready to open in Excel."

- Navigate to **Gantt Chart** as a Dashboard Viewer. Point out it is identical to the Fleet Manager view but contains no interactive controls.

---

### 2.4 Superadmin flow

**Switch to Tab 4 (Superadmin account).**

- Navigate to **User Management**.
- Show the user list: all accounts, their assigned role groups, and last-login timestamps.
- Click **Add User**. Fill in a username and temporary password.
- Assign the user to the **Requester** group. Explain: "Group membership determines what the user can see and do. We'll cover the four roles in detail shortly."
- Save the user.
- Point out: "The Superadmin has all Fleet Manager capabilities plus user account management. The separation means Fleet Managers can do their day-to-day work without being able to accidentally create or delete user accounts."

---

## 3. User Journey Narrative

*Use this section as a script you can narrate while clicking through the app. The story ties every feature together in a realistic scenario.*

---

**Meet Grace.** Grace is a Senior Epidemiologist at ZNPHI in Lusaka. Her team has identified a potential disease cluster in Chipata, Eastern Province, and needs to conduct a field investigation. She needs two vehicles to transport her team and equipment for five days starting in ten days' time.

**Grace submits a transport request.** She logs into the Fleet Manager and clicks **New Request**. She selects **Epidemiology** as her department, enters **8 passengers**, and selects **Eastern Province → Chipata District** using the cascading dropdown — the district list filtered to Eastern Province automatically as soon as she chose it. She sets her departure date to ten days from today.

Because her trip starts in fewer than 14 days, a **yellow late-booking warning** appears. Grace notes the alert and continues — she knows the situation is urgent.

As she completes the form, the system checks for other trips already planned to Chipata. It finds one: a Lab team is travelling to Chipata in four days. A **coordination nudge panel** appears — highlighted, prominent, impossible to miss. The system tells Grace: there is already a trip planned to this district within a 7-day window. Could she share a vehicle with the Labs team? Adjust her dates? At minimum, she should be aware. Grace reads the nudge, decides her team genuinely needs separate vehicles, ticks the **acknowledgment checkbox**, and submits. Her request saves with status **Submitted**.

**The Fleet Manager receives the request.** David, the Fleet Manager, sees the **badge count** on his navigation menu increment. He opens the **Request Queue** and finds Grace's request. It is not flagged as an emergency, but it is sorted by departure date so it appears near the top. He also sees the coordination nudge on the request detail page — the same warning Grace saw.

David opens the **Available Vehicles** panel on Grace's request. The system has already done the filtering: three vehicles are excluded because they have overlapping approved bookings in that period; one more is excluded because it is overdue for a service. David sees a clean list of vehicles that are genuinely available. He selects two Toyota Land Cruisers, assigns two drivers, adds a note: *"Coordinated with Labs team — separate trip justified by different programme areas."* He clicks **Approve**. Two TripAssignment records are created. Grace's request moves to **Approved**.

**The trip begins.** On Grace's departure date, the system's automated task runs at midnight and transitions her request status from **Approved** to **In Progress**. Grace can see this on her **My Requests** page. David sees it in his overview. Nothing needed from either of them — the status updated itself.

**Five days later, the trip ends.** The system's automated task transitions the status from **In Progress** to **Completed**. Both vehicles are now free again. Grace's request now shows a **Completed** badge — and the Cancel button is gone, because there is nothing left to cancel.

**The data appears on the dashboard.** The following morning, a ZNPHI programme director logs in with her **Dashboard Viewer** account. She opens the **KPI Dashboard** and selects the 30-day interval. The Finance panel shows the fuel costs from Grace's trip. The Choropleth Map shows Chipata now has a darker shade — one more trip in that district this month. The Requests by Department bar confirms a spike in Epidemiology requests this period. The director exports the data to CSV for her monthly report.

---

## 4. Edge Cases to Demonstrate

These scenarios show the system's guardrails. Run through each briefly after the main walkthrough.

---

### 4.1 Overdue vehicle blocked from assignment

**How to show it:**

- Log in as Fleet Manager.
- Open any Submitted request in the Request Queue.
- On the assignment screen, point out the Available Vehicles list.
- Navigate separately to **Vehicles & Maintenance** and find a vehicle with a **pulsing red dot** (overdue maintenance).
- Return to the assignment screen and confirm that the red-dot vehicle does not appear in the available list.

**What to say:** "The system enforces this automatically. A Fleet Manager cannot assign an overdue vehicle even if they want to — it is simply absent from the list. The only way to unlock it is to log a maintenance record, which resets the service baseline."

---

### 4.2 Coordination nudge requiring acknowledgment

**How to show it:**

- Log in as Requester.
- Start a new request. Select a province and district that has another trip within the next 7 days in the seed data (**Chipata / Eastern Province** is reliable).
- The coordination nudge panel appears.
- Try to click **Submit** without ticking the acknowledgment checkbox.
- Show that the button remains disabled or the form validation blocks submission.
- Tick the checkbox. The Submit button activates.

**What to say:** "The system does not prevent the trip — Grace's scenario showed that sometimes the overlap is acceptable. But it does require the requester to consciously acknowledge the situation. This reduces accidental duplication and encourages coordination."

---

### 4.3 Late booking warning

**How to show it:**

- On the same New Request form, set the departure date to tomorrow or any date within the next 14 days.
- The yellow warning banner appears immediately on date selection.
- Change the date to 20 days from now. The banner disappears.

**What to say:** "This is a soft warning only — it does not block submission. Its purpose is to flag last-minute requests so the Fleet Manager knows the context when reviewing."

---

### 4.4 Cancel button hidden on non-cancellable requests

**How to show it:**

- Log in as Requester.
- Open **My Requests**.
- Click into a request with status **Rejected** or **Completed**.
- Point out: no Cancel button.
- Click into a request with status **Submitted** or **Approved**.
- Point out: Cancel button is present.

**What to say:** "The cancel action is contextually available — it only appears when cancellation is still meaningful. There is no way to accidentally cancel a trip that has already happened or already been rejected."

---

### 4.5 Dashboard Viewer cannot edit anything

**How to show it:**

- Log in as Dashboard Viewer.
- Navigate to the **KPI Dashboard**, **Gantt Chart**, and **Vehicles** list.
- Point out: no Add, Edit, Approve, Assign, or Export buttons that modify data. All controls are read-only.
- Try to navigate directly to `/bookings/new/` (the request creation URL). The system redirects or returns a permission-denied page.

**What to say:** "The Dashboard Viewer role is deliberately read-only. Leadership and ministry users can see everything without any risk of accidentally modifying operational data."

---

## 5. System Configuration — Settings Page

*Navigate to Settings as Fleet Manager or Superadmin.*

The Settings page controls system-wide behaviour. Changes take effect immediately — no server restart required. Walk through each setting in sequence.

---

### Email notifications

**Toggle: Enable email notifications**

Enables or disables the notification system globally. When enabled, the system sends emails to the configured recipient address on the following events: a new request is submitted (notifies the Fleet Manager), a request is approved or rejected (notifies the Requester).

**Recipient address field**

The email address that receives notifications. In a full deployment, this would typically be the Fleet Manager's email. The field is only active when the toggle is on.

*Tip: during initial deployment, leave notifications off until the email server (SMTP settings in the `.env` file) has been tested. Misconfigured email will not break the application — notifications simply won't send — but it is good practice to confirm delivery before enabling.*

**When to use:** Enable once the organisation has confirmed its SMTP server details and wants live notifications in production.

---

### Buffer days

**Setting: Vehicle booking buffer (days)**

When the system checks whether a vehicle is available for a new trip, it adds a buffer period before and after each existing booking. For example, if the buffer is set to **2 days** and a vehicle is booked to return on a Friday, it will not appear as available for a new trip departing on Saturday or Sunday — only from Monday onwards.

**Real-world impact:** This accounts for the time needed to inspect the vehicle, clean it, refuel it, and handle any post-trip paperwork before it is genuinely ready for the next assignment.

**Typical values:**
- `0` — no buffer; back-to-back bookings are permitted
- `1` — one day's turnaround required
- `2` — two days (recommended for most operations)

*Tip: if Fleet Managers are frequently reporting that vehicles appear available but aren't actually ready, increase the buffer. If the fleet is tight and back-to-back bookings are operationally feasible, reduce it.*

---

### Coordination nudge mode

**Setting: Coordination nudge window**

Controls when the coordination nudge is triggered for a requester selecting a destination district.

| Mode | Behaviour |
|---|---|
| **Exact overlap** | Nudge only when another trip to the same district has dates that directly overlap with the new request |
| **7-day window** | Nudge when another trip is planned to the same district within ±7 days of the new departure date |
| **Custom ± days** | Nudge when another trip is within a custom number of days you specify |

**When to choose each:**

- **Exact overlap** — for large organisations where trips to the same district are routine and a loose time window would trigger too many false nudges, creating alert fatigue.
- **7-day window** — the recommended default for most ZNPHI use cases. A 7-day window is wide enough to catch genuine coordination opportunities (two teams visiting Chipata in the same week could share a vehicle leg) while tight enough not to be disruptive.
- **Custom ± days** — use if 7 days is either too broad or too narrow for your operational rhythm. A field programme that runs monthly visits might use 14 days; a high-tempo response team might prefer 3 days.

*Tip: set this to Exact Overlap during the first few months of deployment to establish a baseline of how often the nudge fires. Once you understand your trip patterns, widen the window if coordination opportunities are being missed.*

---

### Default maintenance interval

**Setting: Service interval (km)**

The number of kilometres between required vehicle services. When a vehicle's recorded mileage exceeds its last-service mileage by more than this value, it turns red and is blocked from assignment.

The **amber warning** triggers when the vehicle is within **500 km** of the interval (this threshold is also configurable — if visible in the Settings page, walk through it here).

**Real-world impact:** Setting this to match your actual service schedule (typically 5,000–10,000 km for the Toyota fleet) ensures the traffic lights accurately reflect maintenance urgency. If set too low, vehicles will appear red too frequently; if set too high, maintenance will be overdue before the system flags it.

**After changing the interval:** The new threshold applies to all vehicles immediately. Vehicles that were amber may become green; vehicles that were green may become amber or red.

*Tip: confirm the correct interval with the ZNPHI transport workshop before go-live. Different vehicle types (Hilux vs Land Cruiser, or older vs newer models) may have different service schedules; the system currently uses a single global interval.*

---

## 6. Adding to the System

The three most common administrative tasks for ongoing system operation.

---

### 6.1 Adding a new vehicle

**Who can do this:** Fleet Manager, Superadmin

**Steps:**

1. Log in and navigate to **Vehicles & Maintenance** in the main navigation.
2. Click the **+ Add Vehicle** button (top right of the page).
3. Fill in the form:

| Field | Notes |
|---|---|
| **Plate number** | Official vehicle registration plate. Must be unique. |
| **Make** | Manufacturer (e.g. Toyota) |
| **Model** | Model name (e.g. Hilux, Land Cruiser) |
| **Year** | Manufacturing year |
| **Seating capacity** | Number of passenger seats (not including driver) |
| **Current mileage** | Odometer reading at the time of adding to the system. Critical: this sets the maintenance baseline. Enter the actual current reading from the vehicle. |
| **Status** | Set to **Available** for a vehicle that is ready for assignments. Use **In Maintenance** if the vehicle is currently being serviced. Use **Out of Service** for a vehicle that is temporarily removed from the fleet. |
| **Province assignment** (if applicable) | Some fleets assign vehicles to provinces; set this if your operational model uses provincial assignment. |
| **Notes** | Optional — any relevant history, special equipment fitted, etc. |

4. Click **Save**. The vehicle appears immediately in the Vehicles list and is available for assignment.

*Tip: after adding the vehicle, navigate to its detail page and verify the maintenance traffic light is green. If it shows amber or red immediately, the mileage entered may have exceeded the service interval — log a maintenance record to reset the baseline.*

---

### 6.2 Adding a new driver

**Who can do this:** Fleet Manager, Superadmin

**Steps:**

1. Navigate to **Drivers** (sub-section of Vehicles & Maintenance, or a separate nav item depending on the current layout).
2. Click **+ Add Driver**.
3. Fill in the form:

| Field | Notes |
|---|---|
| **Full name** | Driver's full legal name |
| **Employee ID / Staff number** | ZNPHI HR identifier |
| **Phone number** | Contact number for coordination |
| **Licence number** | Driving licence number |
| **Licence class** | Class of licence held (relevant if your fleet includes vehicles requiring higher licence classes) |
| **Province** | The province this driver is primarily based in |
| **Status** | Set to **Available**. Use **On Leave** or **Unavailable** when the driver is temporarily not able to take assignments. |
| **Notes** | Optional — any relevant notes |

4. Click **Save**. The driver now appears in the driver selection dropdown on the Request Review & Assignment screen.

*Tip: drivers marked as **Unavailable** are excluded from the assignment dropdown, the same way overdue vehicles are excluded from the vehicle list. Update driver status when they go on leave to prevent accidental assignment.*

---

### 6.3 Creating a new user account and assigning a role

**Who can do this:** Superadmin only

**Steps:**

1. Log in as Superadmin. Navigate to **User Management** in the main navigation.
2. Click **+ Add User**.
3. Enter:
   - **Username** — the account name the user will log in with. Use a consistent format (e.g. `firstname.lastname` or staff number).
   - **Password** — set a temporary password and instruct the user to change it on first login.
   - **First name / Last name** — display name used across the interface.
   - **Email address** — used for notifications if email is enabled.

4. Assign the user to a **Group** (role). The four groups and what they grant:

| Group | Access granted |
|---|---|
| **Requester** | Submit transport requests, view and cancel own requests only. Cannot see other users' requests. Cannot see vehicles, drivers, or analytics. |
| **Fleet Manager** | Full operational access: review all requests, approve/reject, assign vehicles and drivers, manage vehicles and drivers (add, edit, update mileage, log fuel and maintenance), view all analytics and the Gantt chart. Cannot manage user accounts. |
| **Dashboard Viewer** | Read-only access to the KPI Dashboard, Gantt Chart, and vehicle/driver lists. Cannot submit requests, cannot approve or assign anything. Designed for leadership and ministry users. |
| **Superadmin** | All Fleet Manager capabilities, plus User Management (create, edit, deactivate user accounts and assign roles). This account type should be limited to system administrators. |

5. Click **Save**. The user can log in immediately with the assigned role.

*Tip: if a user needs to be deactivated (e.g. they leave the organisation), do not delete their account — uncheck the **Active** checkbox instead. This preserves their historical records (requests they submitted, assignments they approved) while preventing new logins.*

---

## 7. Django Admin Panel Walkthrough

The Django admin is available at `/admin/` and is accessible to Superadmin accounts (or any account with `is_staff = True`).

*Tip: the admin panel is a power tool — use it carefully. Most day-to-day operations should be done through the main application UI. Reserve the admin for the specific tasks described below.*

---

### What is registered in the admin

| Model | Description |
|---|---|
| **Vehicle** | All fleet vehicles |
| **Driver** | All drivers |
| **TransportRequest** | All transport requests across all statuses |
| **TripAssignment** | Assignment records linking requests to vehicles and drivers |
| **FuelRecord** | Fuel fill-up logs per vehicle |
| **MaintenanceRecord** | Service records per vehicle |
| **Settings** | System configuration (singleton — see below) |
| **Province** | The 10 Zambian provinces (reference data) |
| **District** | All 116 districts with province foreign keys (reference data) |
| **Department** | Organisational departments that can make transport requests |
| **User / Group** | Django's built-in user and group management |

---

### When to use the admin panel

**Use the admin for:**

- **Bulk edits or data corrections** — e.g. a batch of vehicle mileage readings were entered incorrectly; the admin's list view allows you to edit multiple records efficiently.
- **Viewing raw records** — if a request is in an unexpected state, the admin lets you inspect every field including internal status flags and timestamps.
- **Editing reference data** — adding a new **Department** (e.g. a new ZNPHI programme unit begins requesting transport), editing Province or District names.
- **User management edge cases** — the main UI handles common user tasks, but the admin gives you direct access to all Django auth fields including permissions, last-login timestamps, and the `is_staff` flag.
- **Diagnosing data issues** — if something looks wrong in the main UI, use the admin to see the underlying data without any presentation layer in the way.

**Do not use the admin for:**

- Submitting, approving, or rejecting transport requests — use the main UI; the admin bypasses status-transition logic and validation.
- Logging fuel or maintenance records — the main UI updates derived fields (maintenance baseline, status) automatically; direct admin edits do not.
- Routine vehicle or driver management — the main UI is safer and faster.
- Creating new user accounts for non-staff users — use the Superadmin's User Management page in the main app.

---

### The Settings model — singleton behaviour

The Settings model holds the system-wide configuration (email toggle, buffer days, nudge mode, maintenance interval). It is enforced as a **singleton**: there can only ever be one Settings record.

In the Django admin, navigate to **Settings**. You will see either:

- One existing row — click it to edit values directly in the admin if needed.
- No rows — this should not happen after a fresh deployment. If it does, click **Add Settings** to create the single row.

**Important:** Do not attempt to add a second Settings row. The application reads only one record; a second row would be silently ignored and could cause confusion. The admin is configured to prevent this, but be aware of the design.

*Tip: prefer the main application's Settings page for configuration changes during normal operation. The admin Settings view is a backup access route if the main UI's Settings page is ever inaccessible.*

---

## 8. Quick Reference Card

### Main application URLs

| URL | Page | Who can access |
|---|---|---|
| `/` | Home / redirect to dashboard | All authenticated users |
| `/accounts/login/` | Login page | Public |
| `/accounts/logout/` | Logout | All authenticated users |
| `/bookings/new/` | New Transport Request form | Requester, Fleet Manager, Superadmin |
| `/bookings/my-requests/` | My Requests list | Requester, Fleet Manager, Superadmin |
| `/bookings/queue/` | Request Queue (all submitted requests) | Fleet Manager, Superadmin |
| `/bookings/<id>/` | Request detail / review & assign | Fleet Manager, Superadmin (full); Requester (own requests only) |
| `/fleet/vehicles/` | Vehicles & Maintenance list | Fleet Manager, Dashboard Viewer, Superadmin |
| `/fleet/vehicles/<id>/` | Vehicle detail | Fleet Manager, Dashboard Viewer, Superadmin |
| `/fleet/drivers/` | Drivers list | Fleet Manager, Dashboard Viewer, Superadmin |
| `/fleet/gantt/` | Gantt Chart | Fleet Manager, Dashboard Viewer, Superadmin |
| `/dashboard/` | KPI Dashboard | Fleet Manager, Dashboard Viewer, Superadmin |
| `/settings/` | System Settings | Fleet Manager, Superadmin |
| `/accounts/users/` | User Management | Superadmin only |
| `/admin/` | Django admin panel | Staff / Superadmin |

---

### Role and permission matrix

| Feature | Requester | Fleet Manager | Dashboard Viewer | Superadmin |
|---|---|---|---|---|
| Submit transport request | Yes | Yes | No | Yes |
| View own requests | Yes | Yes | No | Yes |
| View all requests | No | Yes | No | Yes |
| Cancel own request | Yes (if Submitted/Approved/In Progress) | Yes | No | Yes |
| Approve / reject requests | No | Yes | No | Yes |
| Assign vehicles and drivers | No | Yes | No | Yes |
| View vehicles list | No | Yes | Yes | Yes |
| Add / edit vehicles | No | Yes | No | Yes |
| Log fuel records | No | Yes | No | Yes |
| Log maintenance records | No | Yes | No | Yes |
| View drivers list | No | Yes | Yes | Yes |
| Add / edit drivers | No | Yes | No | Yes |
| View Gantt Chart | No | Yes | Yes | Yes |
| View KPI Dashboard | No | Yes | Yes | Yes |
| Export CSV (any) | No | Yes | Yes (Dashboard only) | Yes |
| Access Settings page | No | Yes | No | Yes |
| User Management | No | No | No | Yes |
| Django admin panel | No | No | No | Yes |

---

*ZNPHI Fleet Manager — Demo & Training Guide | Prepared for ZNPHI stakeholders | Last updated: June 2026*
