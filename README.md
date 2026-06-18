# ZNPHI Fleet Manager

Fleet management web application for ZNPHI (Zambia National Public Health Institute). Built with Django 5, HTMX, Tailwind CSS + DaisyUI, Chart.js, and Leaflet.js.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+

## Local setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd ZNPHI-Fleet-Manager

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the PostgreSQL database
# In psql: CREATE DATABASE znphi_fleet;

# 5. Configure environment
cp .env.example .env
# Edit .env with your database credentials and a secret key

# 6. Run migrations
python manage.py migrate

# 7. Load reference data (provinces, districts, departments)
python manage.py loaddata fixtures/provinces_districts.json
python manage.py loaddata fixtures/departments.json

# 8. Create a superuser
python manage.py createsuperuser

# 9. (Optional) Load synthetic demo data
python manage.py seed_data

# 10. Start the development server
python manage.py runserver
```

## Running tests

```bash
python manage.py test
```

## Project structure

```
fleet_project/   Django project settings and root URLs
accounts/        Authentication, user management, role-based access
bookings/        Transport requests, trip assignments, provinces/districts
fleet/           Vehicles, drivers, fuel records, maintenance records
dashboard/       KPI dashboard, choropleth map
fixtures/        Reference data (provinces, districts, departments)
templates/       Django HTML templates
static/          CSS, JS, fonts
```
