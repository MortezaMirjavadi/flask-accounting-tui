# Terminal Accounting

A personal accounting application with Flask REST API backend and a rich TUI (Terminal User Interface). Supports Jalali (Persian) calendar, multi-user authentication, and PostgreSQL for data persistence.

## Tech Stack

### Backend
- **Flask** - Lightweight web framework with Blueprint-based modular architecture
- **PostgreSQL** - Relational database via `psycopg2`
- **jdatetime** - Jalali (Persian) calendar support

### Frontend
- **Textual** - Modern TUI framework with sidebar navigation, data tables, and custom widgets
- **requests** - HTTP client for API communication

## Features

### Core
- User authentication (register / login)
- Category management (income / cost types)
- Source (account) management with balance tracking
- Transaction recording with Jalali calendar
- Transfer between sources

### Financial Management
- Budget periods and budget items with planned vs. actual tracking
- Check management (issued / received / cashed / bounced)
- Installment plans and payment tracking
- Financial calendar with daily transaction overview

### Reporting
- Daily, weekly, and monthly reports
- Category-based expense/income breakdown
- Summary dashboards with bar and pie charts

### Settings & UX
- Application settings with data reset option
- Sidebar-based TUI navigation
- Jalali date picker widget
- Toman currency formatting

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL

### Setup

1. Clone the repository:
```bash
git clone https://github.com/MortezaMirjavadi/flask-accounting-tui.git
cd terminal_accounting
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL (see [Database Configuration](#database-configuration)).

### Quick Start

```bash
./start.sh
```

This creates the virtual environment, installs dependencies, starts the API server, and launches the TUI.

## Database Configuration

The application uses PostgreSQL. Configure via environment variables:

| Variable      | Default                    | Description               |
|---------------|----------------------------|---------------------------|
| `DATABASE_URL`| *(none)*                   | Full connection string     |
| `DB_HOST`     | `localhost`                | Database host             |
| `DB_PORT`     | `5432`                     | Database port             |
| `DB_NAME`     | `terminal_accounting`      | Database name             |
| `DB_USER`     | `postgres`                 | Database user             |
| `DB_PASSWORD` | *(empty)*                  | Database password         |

`DATABASE_URL` takes precedence over individual variables. Example:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/terminal_accounting"
```

The database schema is created automatically on first run.

## Database Schema

The application uses 11 tables. All tables include `created_at`, `updated_at`, and soft-delete (`deleted_at`) columns. Timestamps auto-update via a `set_updated_at_timestamp()` trigger.

### Entity Relationship Diagram

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│  users   │ 1───N │  categories  │ 1───N │ transactions │
│──────────│       │──────────────│       │──────────────│
│ id (PK)  │       │ id (PK)      │       │ id (PK)      │
│ username │       │ user_id (FK) │       │ user_id (FK) │
│ password │       │ name         │       │ date         │
│ created_at│      │ type         │       │ amount       │
│ updated_at│      │ created_at   │       │ category_id (FK)│
└──────────┘       │ updated_at   │       │ source_id (FK)│
     │             │ deleted_at   │       │ description  │
     │             └──────────────┘       │ reference_type│
     │                                    │ reference_id │
     │             ┌──────────────┐       │ created_at   │
     │        1───N│   sources    │ 1───N │ updated_at   │
     │             │──────────────│       │ deleted_at   │
     │             │ id (PK)      │       └──────────────┘
     │             │ user_id (FK) │
     │             │ name         │       ┌──────────────┐
     │             │ amount       │ 1───N │   transfers  │
     │             │ created_at   │       │──────────────│
     │             │ updated_at   │       │ id (PK)      │
     │             │ deleted_at   │       │ user_id (FK) │
     │             └──────────────┘       │ from_source_id(FK)│
     │                                    │ to_source_id (FK) │
     │             ┌──────────────┐       │ amount       │
     │        1───N│budget_periods│ 1───N │ date         │
     │             │──────────────│       │ notes        │
     │             │ id (PK)      │       │ created_at   │
     │             │ user_id (FK) │       │ updated_at   │
     │             │ year         │       │ deleted_at   │
     │             │ month        │       └──────────────┘
     │             │ created_at   │
     │             │ updated_at   │       ┌──────────────────┐
     │             │ deleted_at   │       │installment_plans │
     │             └──────────────┘       │──────────────────│
     │                  │ 1               │ id (PK)          │
     │                  │                 │ user_id (FK)     │
     │                  │ N               │ title            │
     │             ┌──────────────┐       │ total_amount     │
     │             │ budget_items │       │ installment_count│
     │             │──────────────│       │ installment_amount│
     │             │ id (PK)      │       │ start_date       │
     │             │ budget_period│       │ due_day_of_month │
     │             │   _id (FK)   │       │ category_id (FK) │
     │             │ category_id  │       │ source_id (FK)   │
     │             │   (FK)       │       │ status           │
     │             │ planned_amount│      │ created_at       │
     │             │ notes        │       │ updated_at       │
     │             │ created_at   │       │ deleted_at       │
     │             │ updated_at   │       └──────────────────┘
     │             │ deleted_at   │              │ 1
     │             └──────────────┘              │
     │                                     ┌──────────────┐
     │             ┌──────────────┐    1───N│ installments │
     │        1───N│   checks     │        │──────────────│
     │             │──────────────│        │ id (PK)      │
     │             │ id (PK)      │        │ plan_id (FK) │
     │             │ user_id (FK) │        │ installment  │
     │             │ check_number │        │   _number    │
     │             │ bank_name    │        │ amount       │
     │             │ amount       │        │ due_date     │
     │             │ issue_date   │        │ paid_date    │
     │             │ due_date     │        │ status       │
     │             │ type         │        │ transaction_id(FK)│
     │             │ source_id(FK)│        │ created_at   │
     │             │ category_id(FK)│      │ updated_at   │
     │             │ status       │        │ deleted_at   │
     │             │ transaction_id(FK)│   └──────────────┘
     │             │ description  │
     │             │ created_at   │       ┌────────────────────┐
     │             │ updated_at   │       │  financial_events  │
     │             │ deleted_at   │       │────────────────────│
     │             └──────────────┘       │ id (PK)            │
     │                                    │ user_id (FK)       │
     └────────────────────────────────────│ title              │
                                          │ description        │
                                          │ amount             │
                                          │ category_id (FK)   │
                                          │ source_id (FK)     │
                                          │ frequency          │
                                          │ repeat_interval    │
                                          │ start_date         │
                                          │ end_date           │
                                          │ occurrence_limit   │
                                          │ status             │
                                          │ deleted_at         │
                                          └────────────────────┘
                                                   │ 1
                                                   │ N
                                          ┌──────────────────────────┐
                                          │financial_event_instances │
                                          │──────────────────────────│
                                          │ id (PK)                  │
                                          │ event_id (FK)            │
                                          │ user_id (FK)             │
                                          │ due_date                 │
                                          │ status                   │
                                          │ snoozed_from             │
                                          │ transaction_id (FK)      │
                                          │ created_at               │
                                          │ updated_at               │
                                          └──────────────────────────┘
```

### Table Definitions

#### users
| Column         | Type         | Constraints                    |
|----------------|--------------|--------------------------------|
| id             | SERIAL       | PRIMARY KEY                    |
| username       | VARCHAR(255) | NOT NULL, UNIQUE               |
| password_hash  | VARCHAR(255) | NOT NULL                       |
| created_at     | TIMESTAMP    | NOT NULL, DEFAULT NOW()        |
| updated_at     | TIMESTAMP    | NOT NULL, DEFAULT NOW()        |

#### categories
| Column     | Type         | Constraints                         |
|------------|--------------|-------------------------------------|
| id         | SERIAL       | PRIMARY KEY                         |
| user_id    | INTEGER      | NOT NULL, FK -> users(id)           |
| name       | VARCHAR(255) | NOT NULL                            |
| type       | VARCHAR(50)  | NOT NULL, CHECK IN ('income','cost')|
| created_at | TIMESTAMP    | NOT NULL, DEFAULT NOW()             |
| updated_at | TIMESTAMP    | NOT NULL, DEFAULT NOW()             |
| deleted_at | TIMESTAMP    | NULLABLE (soft delete)              |
|            |              | UNIQUE(user_id, name)               |

#### sources
| Column     | Type           | Constraints                    |
|------------|----------------|--------------------------------|
| id         | SERIAL         | PRIMARY KEY                    |
| user_id    | INTEGER        | NOT NULL, FK -> users(id)      |
| name       | VARCHAR(255)   | NOT NULL                       |
| amount     | NUMERIC(15, 2) | NOT NULL, DEFAULT 0            |
| created_at | TIMESTAMP      | NOT NULL, DEFAULT NOW()        |
| updated_at | TIMESTAMP      | NOT NULL, DEFAULT NOW()        |
| deleted_at | TIMESTAMP      | NULLABLE (soft delete)         |
|            |                | UNIQUE(user_id, name)          |

#### transactions
| Column        | Type           | Constraints                         |
|---------------|----------------|-------------------------------------|
| id            | SERIAL         | PRIMARY KEY                         |
| user_id       | INTEGER        | NOT NULL, FK -> users(id)           |
| date          | DATE           | NOT NULL (stored as Gregorian)      |
| amount        | NUMERIC(15, 2) | NOT NULL                            |
| category_id   | INTEGER        | NOT NULL, FK -> categories(id)      |
| source_id     | INTEGER        | FK -> sources(id)                   |
| description   | TEXT           |                                     |
| reference_type| TEXT           | e.g. 'check', 'installment'        |
| reference_id  | INTEGER        | links to originating record         |
| created_at    | TIMESTAMP      | NOT NULL, DEFAULT NOW()             |
| updated_at    | TIMESTAMP      | NOT NULL, DEFAULT NOW()             |
| deleted_at    | TIMESTAMP      | NULLABLE (soft delete)              |

#### transfers
| Column         | Type           | Constraints                           |
|----------------|----------------|---------------------------------------|
| id             | SERIAL         | PRIMARY KEY                           |
| user_id        | INTEGER        | NOT NULL, FK -> users(id) ON DELETE CASCADE |
| from_source_id | INTEGER        | NOT NULL, FK -> sources(id)           |
| to_source_id   | INTEGER        | NOT NULL, FK -> sources(id)           |
| amount         | NUMERIC(15, 2) | NOT NULL, CHECK > 0                   |
| date           | DATE           | NOT NULL                              |
| notes          | TEXT           |                                       |
| created_at     | TIMESTAMP      | NOT NULL, DEFAULT NOW()               |
| updated_at     | TIMESTAMP      | NOT NULL, DEFAULT NOW()               |
| deleted_at     | TIMESTAMP      | NULLABLE (soft delete)                |
|                |                | CHECK(from_source_id != to_source_id) |

#### budget_periods
| Column     | Type      | Constraints                       |
|------------|-----------|-----------------------------------|
| id         | SERIAL    | PRIMARY KEY                       |
| user_id    | INTEGER   | NOT NULL, FK -> users(id)         |
| year       | INTEGER   | NOT NULL                          |
| month      | INTEGER   | NOT NULL, CHECK BETWEEN 1 AND 12  |
| created_at | TIMESTAMP | DEFAULT NOW()                     |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW()           |
| deleted_at | TIMESTAMP | NULLABLE (soft delete)            |
|            |           | UNIQUE(user_id, year, month)      |

#### budget_items
| Column          | Type           | Constraints                   |
|-----------------|----------------|-------------------------------|
| id              | SERIAL         | PRIMARY KEY                   |
| budget_period_id| INTEGER        | NOT NULL, FK -> budget_periods(id) ON DELETE CASCADE |
| category_id     | INTEGER        | NOT NULL, FK -> categories(id)|
| planned_amount  | NUMERIC(15, 2) | NOT NULL                      |
| notes           | TEXT           |                               |
| created_at      | TIMESTAMP      | DEFAULT NOW()                 |
| updated_at      | TIMESTAMP      | NOT NULL, DEFAULT NOW()       |
| deleted_at      | TIMESTAMP      | NULLABLE (soft delete)        |
|                 |                | UNIQUE(budget_period_id, category_id) |

#### installment_plans
| Column             | Type           | Constraints                                    |
|--------------------|----------------|------------------------------------------------|
| id                 | SERIAL         | PRIMARY KEY                                    |
| user_id            | INTEGER        | NOT NULL, FK -> users(id)                      |
| title              | VARCHAR(255)   | NOT NULL                                       |
| total_amount       | NUMERIC(15, 2) | NOT NULL, CHECK >= 0                           |
| installment_count  | INTEGER        | NOT NULL, CHECK > 0                            |
| installment_amount | NUMERIC(15, 2) | NOT NULL, CHECK >= 0                           |
| start_date         | DATE           | NOT NULL                                       |
| due_day_of_month   | INTEGER        | NOT NULL, CHECK BETWEEN 1 AND 31               |
| category_id        | INTEGER        | NOT NULL, FK -> categories(id)                 |
| source_id          | INTEGER        | FK -> sources(id)                              |
| status             | VARCHAR(20)    | NOT NULL, DEFAULT 'active', CHECK IN ('active','completed','canceled') |
| created_at         | TIMESTAMP      | NOT NULL, DEFAULT NOW()                        |
| updated_at         | TIMESTAMP      | NOT NULL, DEFAULT NOW()                        |
| deleted_at         | TIMESTAMP      | NULLABLE (soft delete)                         |

#### installments
| Column           | Type           | Constraints                                    |
|------------------|----------------|------------------------------------------------|
| id               | SERIAL         | PRIMARY KEY                                    |
| plan_id          | INTEGER        | NOT NULL, FK -> installment_plans(id) ON DELETE CASCADE |
| installment_number| INTEGER       | NOT NULL, CHECK > 0                            |
| amount           | NUMERIC(15, 2) | NOT NULL, CHECK >= 0                           |
| due_date         | DATE           | NOT NULL                                       |
| paid_date        | DATE           | NULLABLE                                       |
| status           | VARCHAR(20)    | NOT NULL, DEFAULT 'pending', CHECK IN ('pending','paid','overdue') |
| transaction_id   | INTEGER        | FK -> transactions(id)                         |
| created_at       | TIMESTAMP      | NOT NULL, DEFAULT NOW()                        |
| updated_at       | TIMESTAMP      | NOT NULL, DEFAULT NOW()                        |
| deleted_at       | TIMESTAMP      | NULLABLE (soft delete)                         |
|                  |                | UNIQUE(plan_id, installment_number)            |

#### checks
| Column         | Type           | Constraints                                    |
|----------------|----------------|------------------------------------------------|
| id             | SERIAL         | PRIMARY KEY                                    |
| user_id        | INTEGER        | NOT NULL, FK -> users(id)                      |
| check_number   | VARCHAR(100)   |                                                |
| bank_name      | VARCHAR(255)   |                                                |
| amount         | NUMERIC(15, 2) | NOT NULL, CHECK >= 0                           |
| issue_date     | DATE           | NOT NULL                                       |
| due_date       | DATE           | NOT NULL                                       |
| type           | VARCHAR(20)    | NOT NULL, CHECK IN ('issued','received')        |
| source_id      | INTEGER        | FK -> sources(id)                              |
| category_id    | INTEGER        | NOT NULL, FK -> categories(id)                 |
| status         | VARCHAR(20)    | NOT NULL, DEFAULT 'pending', CHECK IN ('pending','cleared','bounced','canceled') |
| transaction_id | INTEGER        | FK -> transactions(id)                         |
| description    | TEXT           |                                                |
| created_at     | TIMESTAMP      | NOT NULL, DEFAULT NOW()                        |
| updated_at     | TIMESTAMP      | NOT NULL, DEFAULT NOW()                        |
| deleted_at     | TIMESTAMP      | NULLABLE (soft delete)                         |

#### financial_events
| Column           | Type           | Constraints                              |
|------------------|----------------|------------------------------------------|
| id               | SERIAL         | PRIMARY KEY                              |
| user_id          | INTEGER        | NOT NULL, FK -> users(id)                |
| title            | VARCHAR(500)   | NOT NULL                                 |
| description      | TEXT           |                                          |
| amount           | NUMERIC(15, 2) | NOT NULL                                 |
| category_id      | INTEGER        | NOT NULL, FK -> categories(id)           |
| source_id        | INTEGER        | FK -> sources(id)                        |
| frequency        | VARCHAR(50)    | NOT NULL, DEFAULT 'once'                 |
| repeat_interval  | INTEGER        | NOT NULL, DEFAULT 1                      |
| start_date       | DATE           | NOT NULL                                 |
| end_date         | DATE           |                                          |
| occurrence_limit | INTEGER        |                                          |
| status           | VARCHAR(50)    | NOT NULL, DEFAULT 'active'               |
| created_at       | TIMESTAMP      | DEFAULT NOW()                            |
| updated_at       | TIMESTAMP      | NOT NULL, DEFAULT NOW()                  |
| last_modified_at | TIMESTAMP      | DEFAULT NOW()                            |
| deleted_at       | TIMESTAMP      | NULLABLE (soft delete)                   |

#### financial_event_instances
| Column           | Type      | Constraints                              |
|------------------|-----------|------------------------------------------|
| id               | SERIAL    | PRIMARY KEY                              |
| event_id         | INTEGER   | NOT NULL, FK -> financial_events(id) ON DELETE CASCADE |
| user_id          | INTEGER   | NOT NULL, FK -> users(id)                |
| due_date         | DATE      | NOT NULL                                 |
| status           | VARCHAR(50)| NOT NULL, DEFAULT 'pending'             |
| snoozed_from     | DATE      |                                          |
| transaction_id   | INTEGER   | FK -> transactions(id)                   |
| created_at       | TIMESTAMP | DEFAULT NOW()                            |
| updated_at       | TIMESTAMP | NOT NULL, DEFAULT NOW()                  |
| last_modified_at | TIMESTAMP | DEFAULT NOW()                            |

### Key Relationships
- **users** 1:N **categories** - each user owns their categories
- **users** 1:N **sources** - each user owns their accounts
- **users** 1:N **transactions** - each user owns their transactions
- **categories** 1:N **transactions** - each category groups many transactions
- **sources** 1:N **transactions** - each source has many transactions
- **users** 1:N **transfers** - transfers between a user's own sources
- **sources** 1:N **transfers** (from/to) - a source can be origin or destination
- **users** 1:N **budget_periods** - each user has monthly budget periods
- **budget_periods** 1:N **budget_items** - each period has category-level items
- **users** 1:N **installment_plans** - each user owns their installment plans
- **installment_plans** 1:N **installments** - each plan has individual payment records
- **users** 1:N **checks** - each user owns their checks
- **users** 1:N **financial_events** - recurring or one-time financial events
- **financial_events** 1:N **financial_event_instances** - generated occurrences
- **transactions** can reference **checks** or **installments** via `reference_type`/`reference_id`

## Usage

### 1. Start the API Server

```bash
python run_api.py
```

The API runs on `http://127.0.0.1:5000`.

### 2. Launch the TUI

```bash
python run_tui.py
```

Or run both together:
```bash
./start.sh
```

## API Endpoints

All endpoints except `/auth/*` require the `X-Username` header (or `?username=` query param) to identify the user.

### Authentication
| Method | Endpoint          | Description         | Body                                      |
|--------|-------------------|---------------------|-------------------------------------------|
| POST   | `/auth/register`  | Register a new user | `{"username":"...","password":"..."}`      |
| POST   | `/auth/login`     | Login               | `{"username":"...","password":"..."}`      |
| GET    | `/auth/me`        | Get user info       | `?username=...`                           |

### Categories
| Method | Endpoint           | Description               | Body / Params                            |
|--------|--------------------|---------------------------|------------------------------------------|
| GET    | `/categories`      | List categories           | `?name=&type=income\|cost`               |
| GET    | `/categories/<id>` | Get single category       |                                          |
| POST   | `/categories`      | Create category           | `{"name":"...","type":"income\|cost"}`   |
| PUT    | `/categories/<id>` | Update category           | `{"name":"...","type":"income\|cost"}`   |
| DELETE | `/categories/<id>` | Soft-delete category      |                                          |

### Sources
| Method | Endpoint                   | Description                 | Body / Params                                 |
|--------|----------------------------|-----------------------------|-----------------------------------------------|
| GET    | `/sources`                 | List sources                | `?name=&min_amount=&max_amount=`              |
| GET    | `/sources/<id>`            | Get single source           |                                               |
| POST   | `/sources`                 | Create source               | `{"name":"...","amount":0}`                   |
| PUT    | `/sources/<id>`            | Update source               | `{"name":"...","amount":0}`                   |
| DELETE | `/sources/<id>`            | Soft-delete source          |                                               |
| GET    | `/sources/<id>/balance`    | Get source balance          |                                               |
| GET    | `/sources/<id>/transfers`  | List transfers for source   |                                               |

### Transactions
| Method | Endpoint              | Description                        | Body / Params                              |
|--------|-----------------------|------------------------------------|--------------------------------------------|
| GET    | `/transactions`       | List transactions (and transfers)  | `?category_id=&source_id=&date_from=&date_to=&min_amount=&max_amount=&description=&category_type=&include_transfers=` |
| GET    | `/transactions/<id>`  | Get single transaction             | `?record_type=transfer`                    |
| POST   | `/transactions`       | Create transaction or transfer     | *(see bodies below)*                       |
| PUT    | `/transactions/<id>`  | Update transaction or transfer     | *(see bodies below)*                       |
| DELETE | `/transactions/<id>`  | Soft-delete transaction            | `?record_type=transfer`                    |

**Transaction body:**
```json
{
  "date": "1403-01-15",
  "amount": 5000,
  "category_id": 1,
  "source_id": 1,
  "description": "..."
}
```

**Transfer body (via transactions):**
```json
{
  "is_transfer": true,
  "date": "1403-01-15",
  "amount": 10000,
  "from_source_id": 1,
  "to_source_id": 2,
  "notes": "..."
}
```

### Budget
| Method | Endpoint                       | Description                   | Body / Params                 |
|--------|--------------------------------|-------------------------------|-------------------------------|
| GET    | `/budget/periods`              | List budget periods           | `?year=&month=`              |
| GET    | `/budget/periods/with-items`   | List periods with their items | `?year=&month=`              |
| GET    | `/budget/periods/<id>`         | Get single period             |                               |
| POST   | `/budget/periods`              | Create budget period          | `{"year":1403,"month":1}`    |
| PUT    | `/budget/periods/<id>`         | Update budget period          | `{"year":1403,"month":2}`    |
| DELETE | `/budget/periods/<id>`         | Soft-delete period            |                               |
| GET    | `/budget/periods/<id>/items`   | List items for a period       |                               |
| GET    | `/budget/items/<id>`           | Get single item               |                               |
| POST   | `/budget/items`                | Create budget item            | `{"budget_period_id":1,"category_id":1,"planned_amount":5000,"notes":"..."}` |
| PUT    | `/budget/items/<id>`           | Update budget item            | `{"category_id":1,"planned_amount":5000,"notes":"..."}` |
| DELETE | `/budget/items/<id>`           | Soft-delete item              |                               |

### Checks
| Method | Endpoint                      | Description           | Body / Params                            |
|--------|-------------------------------|-----------------------|------------------------------------------|
| GET    | `/checks`                     | List checks           | `?status=&bank_name=&check_number=&type=`|
| GET    | `/checks/upcoming`            | Upcoming checks       | `?days=30`                               |
| GET    | `/checks/<id>`                | Get single check      |                                          |
| POST   | `/checks`                     | Create check          | *(see body below)*                       |
| POST   | `/checks/<id>/clear`          | Mark check as cleared | `{"cleared_date":"1403-02-01"}`          |
| POST   | `/checks/<id>/bounce`         | Mark check as bounced |                                          |
| POST   | `/checks/<id>/cancel`         | Cancel check          |                                          |
| PUT    | `/checks/<id>/due-date`       | Change due date       | `{"due_date":"1403-03-15"}`              |

**Check body:**
```json
{
  "type": "issued",
  "check_number": "123456",
  "bank_name": "Bank Melli",
  "amount": 50000,
  "issue_date": "1403-01-01",
  "due_date": "1403-04-01",
  "category_id": 1,
  "source_id": 1,
  "description": "..."
}
```

### Installments
| Method | Endpoint                          | Description               | Body / Params                            |
|--------|-----------------------------------|---------------------------|------------------------------------------|
| GET    | `/installments/plans`             | List installment plans    | `?status=`                               |
| GET    | `/installments/upcoming`          | Upcoming installments     | `?days=30`                               |
| GET    | `/installments/overdue`           | Overdue installments      |                                          |
| GET    | `/installments/debt`              | Remaining debt summary    |                                          |
| GET    | `/installments/plans/<id>`        | Get plan with installments|                                          |
| POST   | `/installments/plans`             | Create plan               | *(see body below)*                       |
| POST   | `/installments/plans/<id>/generate` | Regenerate installments |                                          |
| POST   | `/installments/plans/<id>/cancel` | Cancel plan               |                                          |
| POST   | `/installments/pay`               | Mark installments paid    | `{"installment_ids":[1,2],"paid_date":"1403-02-01"}` |
| PUT    | `/installments/<id>/due-date`     | Change installment due date | `{"due_date":"1403-03-15"}`            |

**Installment plan body:**
```json
{
  "title": "Car loan",
  "total_amount": 500000,
  "installment_count": 12,
  "installment_amount": 41667,
  "start_date": "1403-01-01",
  "due_day_of_month": 1,
  "category_id": 1,
  "source_id": 1,
  "status": "active"
}
```

### Reports
| Method | Endpoint                          | Description                       | Params               |
|--------|-----------------------------------|-----------------------------------|----------------------|
| GET    | `/reports/daily`                  | Daily report                      | `?date=`             |
| GET    | `/reports/weekly`                 | Weekly report                     | `?start_date=`       |
| GET    | `/reports/monthly`                | Monthly report                    | `?year=&month=`      |
| GET    | `/reports/transactions/summary`   | Current month summary             |                      |
| GET    | `/reports/transactions/category`  | Current month by category         |                      |
| GET    | `/reports/transactions/monthly`   | Last 6 months trend               |                      |
| GET    | `/reports/transactions/category-chart` | Current month category chart |                      |
| GET    | `/reports/budget`                 | Budget vs actual report           | `?year=&month=`      |

### Settings
| Method | Endpoint         | Description                          |
|--------|------------------|--------------------------------------|
| POST   | `/settings/reset`| Soft-delete all user data            |

## TUI Screens

| Screen         | Description                                    |
|----------------|------------------------------------------------|
| Login          | User authentication                            |
| Main Menu      | Top-level navigation with sidebar              |
| Categories     | CRUD for income/cost categories                |
| Sources        | Account management with balance overview       |
| Transactions   | Transaction list, add/edit with Jalali picker  |
| Budget         | Budget periods, items, and reports             |
| Reports        | Daily/weekly/monthly summaries with charts     |
| Checks         | Check lifecycle management                     |
| Installments   | Installment plan and payment tracking          |
| Settings       | App settings and data management               |
| Calendar       | Financial calendar with daily overview         |

## Date Format

All dates use **Jalali (Persian) calendar** in `YYYY-MM-DD` format (e.g., `1403-01-15`). The system converts between Jalali and Gregorian for storage automatically.

## Project Structure

```
terminal_accounting/
├── app/                    # Flask API application
│   ├── __init__.py         # App factory (create_app)
│   ├── config.py           # Configuration classes
│   ├── extensions.py       # Flask extensions
│   ├── models/             # Request validation
│   ├── routes/             # Blueprint modules
│   │   ├── auth.py
│   │   ├── budget.py
│   │   ├── categories.py
│   │   ├── checks.py
│   │   ├── installments.py
│   │   ├── reports.py
│   │   ├── settings.py
│   │   ├── sources.py
│   │   └── transactions.py
│   ├── services/           # Business logic
│   └── utils/              # Helpers and decorators
├── services/               # Domain services
│   ├── alert_service.py
│   ├── calendar_service.py
│   ├── check_service.py
│   ├── forecast_service.py
│   └── installment_service.py
├── tui/                    # Terminal UI application
│   ├── app.py              # Main TUI app
│   ├── api/                # API client
│   ├── screens/            # Screen modules
│   ├── widgets/            # Custom Textual widgets
│   ├── calendar_view.py    # Financial calendar
│   ├── config.py           # TUI configuration
│   └── jalali_date_picker.py
├── database.py             # PostgreSQL connection pool
├── main.py                 # CLI entry point
├── run_api.py              # API server launcher
├── run_tui.py              # TUI launcher
├── start.sh                # Combined launcher script
└── requirements.txt
```

## API Examples

### Register a User
```bash
curl -X POST http://127.0.0.1:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "morteza", "password": "securepass"}'
```

### Login
```bash
curl -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "morteza", "password": "securepass"}'
```

### Create a Transaction
```bash
curl -X POST http://127.0.0.1:5000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "username": "morteza",
    "date": "1403-01-15",
    "amount": 5000,
    "category_id": 1,
    "source_id": 1,
    "description": "Monthly salary"
  }'
```

### Transfer Between Sources
```bash
curl -X POST http://127.0.0.1:5000/sources/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "username": "morteza",
    "from_source_id": 1,
    "to_source_id": 2,
    "amount": 10000
  }'
```

### Get Daily Report
```bash
curl "http://127.0.0.1:5000/reports/daily?username=morteza&date=1403-01-15"
```

## License

MIT

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
