# Workshop Management System

A workshop (auto repair shop) operations management application, customer, vehicle, service history, and sparepart stock tracking, with automation for vehicle status classification and automatic customer follow-up.

## Project Status

**Actively in development**, Step 4 of 7 in the implementation roadmap (models, admin, and business logic/signals are done; custom dashboard, follow-up page, and daily background job are not yet built).

## Why This Project Exists

Most small to medium-sized workshops still track service history and sparepart stock manually, making it hard to know which vehicles need a follow-up call and which spareparts are running low. This project is built as a freelance portfolio piece for the auto repair shop niche, with operational CRUD as the foundation and follow-up automation as the differentiating layer on top.

## Features

### Implemented

- Customer, Vehicle, and service history tracking (ServiceRecord with the spareparts used)
- Automatic sparepart stock deduction, calculated as a delta when quantity is edited rather than a full re-deduction each time
- Automatic vehicle status classification (NEW / ACTIVE / INACTIVE), recomputed from the service history that actually remains every time a record is created, edited, or deleted
- Automatic follow-up creation for new customers on their first recorded service
- Data validation: a sparepart cannot be swapped on an existing service item, an odometer value that has already been filled in cannot be cleared, stock cannot go negative
- Warning shown in Django Admin before deleting service records that have wide-reaching side effects (stock, status, follow-ups)
- Role-based access (Owner vs Admin/Cashier), the Owner has full access including manual status correction, while Admin/Cashier is limited to daily operations

### Planned

- Custom dashboard (operational statistics, follow-up priority list)
- Follow-up page with WhatsApp integration (wa.me link with a pre-filled message template)
- Automatic reactivation detection via Celery Beat (daily batch job)
- Realistic demo data and containerization (Docker)

## Design Decisions

This section documents technical decisions significant enough to explain, not just what was built.

**Stock deduction uses a delta, not a full replace.** Editing `quantity_used` from 2 to 3 only reduces stock by 1, calculated through `pre_save`/`post_save` signals and applied with a database-level `F()` expression rather than a read-then-write in Python, making it safe against race conditions when two admins record the same sparepart at the same time.

**A sparepart on a service item cannot be swapped once created.** Allowing a swap would require the system to track which stock to restore and which to deduct at the same time. Correcting a mistaken entry is done by deleting and recreating the item instead of editing the sparepart field.

**Vehicle status is recomputed, not manually toggled.** A single function, `recompute_vehicle_status()`, always looks at whichever service record is actually the most recent in the database to determine status, and is called on every create, update, and delete of a ServiceRecord. This replaced separate manual logic per scenario, and is naturally correct even for non-linear cases, deleting the record that reactivated a vehicle can put it back to inactive, depending on what history remains.

**Follow-ups are never modified or deleted automatically by the system.** New-customer and reactivation follow-ups persist even when the underlying service history changes. Instead, the Admin sees an explicit warning before deleting service data with wide-reaching effects. This was decided after considering several automated approaches (including deleting follow-ups under certain conditions) that ultimately added more complexity than the rare real-world scenario justified for a single-workshop daily operation.

**Odometer has two distinct "empty" cases, handled differently.** A new record without an odometer reading (e.g., a quick wash service) is left as-is, and the system keeps using the odometer value from an older record. Editing an already-filled odometer value down to empty is blocked by validation, since it would leave the vehicle's data pointing to a number no longer backed by any visible record.

## Tech Stack

**Backend:** Django, Django REST Framework, PostgreSQL, Celery + Redis (background jobs), django-celery-beat

**Frontend (planned):** Django Templates + HTMX, Tailwind CSS

**Infrastructure (planned):** Docker + docker-compose, Gunicorn, Nginx

## App Structure

```
project_root/
├── accounts/      - User (custom, extends AbstractUser + role)
├── customers/     - Customer, Vehicle
├── services/      - ServiceRecord, ServiceRecordItem
├── inventory/     - Sparepart
└── automation/    - FollowUp, AutomationSetting
```

Split by domain rather than a single large app, so navigation stays clear as the project grows, and each app has its own scoped `admin.py`, `models.py`, and `views.py`.

## Getting Started

```bash
# clone and enter the project folder
git clone <repo-url>
cd bengkel-ops

# create a virtual environment and install dependencies
python -m venv env
source env/bin/activate
pip install -r requirements.txt

# copy and adjust environment variables
cp .env.example .env

# run database migrations
python manage.py migrate

# create a superuser account
python manage.py createsuperuser

# start the development server
python manage.py runserver
```

Visit `/admin/` to access Django Admin and start entering Customer, Vehicle, and ServiceRecord data.

## Contact

[LinkedIn](https://www.linkedin.com/in/iqbal-julianto-325781408)
