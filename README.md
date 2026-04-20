# Terminal Accounting

A personal accounting application with Flask REST API backend and multiple frontend interfaces (CLI, TUI). Supports Jalali (Persian) calendar for date handling.

## Tech Stack

### Backend
- **Flask** - Lightweight web framework for REST API
- **SQLite** - Embedded database for data persistence
- **jdatetime** - Jalali (Persian) calendar support

### Frontend
- **Textual** - Modern TUI (Terminal User Interface) framework
- **requests** - HTTP client for API communication
- **argparse** - CLI argument parsing

### Database Schema

#### Tables

**categories**
```
┌────────────┬──────────┬─────────────┬─────────────────────────────┐
│ Column     │ Type     │ Constraints │ Description                 │
├────────────┼──────────┼─────────────┼─────────────────────────────┤
│ id         │ INTEGER  │ PRIMARY KEY │ Auto-increment ID           │
│ name       │ TEXT     │ NOT NULL    │ Category name (unique)      │
│            │          │ UNIQUE      │                             │
│ type       │ TEXT     │ NOT NULL    │ 'income' or 'cost'          │
│            │          │ CHECK       │                             │
└────────────┴──────────┴─────────────┴─────────────────────────────┘
```

**sources**
```
┌────────────┬──────────┬─────────────┬─────────────────────────────┐
│ Column     │ Type     │ Constraints │ Description                 │
├────────────┼──────────┼─────────────┼─────────────────────────────┤
│ id         │ INTEGER  │ PRIMARY KEY │ Auto-increment ID           │
│ name       │ TEXT     │ NOT NULL    │ Source name (unique)        │
│            │          │ UNIQUE      │                             │
│ amount     │ REAL     │ NOT NULL    │ Current balance             │
│            │          │ DEFAULT 0   │                             │
└────────────┴──────────┴─────────────┴─────────────────────────────┘
```

**transactions**
```
┌─────────────┬──────────┬─────────────┬─────────────────────────────┐
│ Column      │ Type     │ Constraints │ Description                 │
├─────────────┼──────────┼─────────────┼─────────────────────────────┤
│ id          │ INTEGER  │ PRIMARY KEY │ Auto-increment ID           │
│ date        │ TEXT     │ NOT NULL    │ Transaction date (Gregorian)│
│ amount      │ REAL     │ NOT NULL    │ Transaction amount          │
│ category_id │ INTEGER  │ FOREIGN KEY │ References categories(id)   │
│ source_id   │ INTEGER  │ FOREIGN KEY │ References sources(id)      │
│ description │ TEXT     │             │ Optional description        │
│ created_at  │ TEXT     │ DEFAULT     │ Timestamp (auto-generated)  │
│             │          │ CURRENT_TS  │                             │
└─────────────┴──────────┴─────────────┴─────────────────────────────┘
```

#### Entity Relationships

```
┌──────────────┐
│  categories  │
│──────────────│
│ id (PK)      │
│ name         │
│ type         │
└──────────────┘
       │
       │ 1
       │
       │
       │ *
       ▼
┌──────────────┐         ┌──────────────┐
│ transactions │    *    │   sources    │
│──────────────│◄────────│──────────────│
│ id (PK)      │         │ id (PK)      │
│ date         │    1    │ name         │
│ amount       │         │ amount       │
│ category_id  │         └──────────────┘
│ source_id    │
│ description  │
│ created_at   │
└──────────────┘
```

**Relationships:**
- One category can have many transactions (1:N)
- One source can have many transactions (1:N)
- Transactions store dates in Gregorian format internally
- API accepts/returns dates in Jalali format (YYYY-MM-DD)

## Features

- ✅ Category management (income/cost types)
- ✅ Source management with balance tracking
- ✅ Transaction recording with Jalali calendar
- ✅ Balance calculations per source
- ✅ RESTful API endpoints
- ✅ CLI interface for quick operations
- ✅ TUI interface for interactive usage

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
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

## Usage

### 1. Start the Flask API Server

```bash
python app.py
```

The API will run on `http://127.0.0.1:5000` by default.

**Available Endpoints:**

- `GET /categories` - List all categories
- `POST /categories` - Create category (body: `{"name": "...", "type": "income|cost"}`)
- `PUT /categories/<id>` - Update category
- `DELETE /categories/<id>` - Delete category

- `GET /sources` - List all sources
- `POST /sources` - Create source (body: `{"name": "...", "amount": 0}`)
- `PUT /sources/<id>` - Update source
- `DELETE /sources/<id>` - Delete source
- `GET /sources/<id>/balance` - Get source balance

- `GET /transactions` - List transactions (supports `?source_id=<id>`)
- `POST /transactions` - Create transaction (body: `{"date": "1403-01-15", "amount": 1000, "category_id": 1, "source_id": 1, "description": "..."}`)
- `PUT /transactions/<id>` - Update transaction
- `DELETE /transactions/<id>` - Delete transaction

### 2. CLI Interface

Run commands directly from terminal:

```bash
# Categories
python cli.py category list
python cli.py category create --name "Salary" --type income
python cli.py category update --id 1 --name "Monthly Salary"
python cli.py category delete --id 1

# Sources
python cli.py source list
python cli.py source create --name "Bank Melli" --amount 10000
python cli.py source update --id 1 --name "Bank Sepah"
python cli.py source delete --id 1
python cli.py source balance --id 1

# Transactions
python cli.py transaction list
python cli.py transaction list --source-id 1
python cli.py transaction create --date "1403-01-15" --amount 5000 --category-id 1 --source-id 1 --description "Salary payment"
python cli.py transaction update --id 1 --amount 5500
python cli.py transaction delete --id 1
```

### 3. TUI Interface

Launch the interactive terminal UI:

```bash
python tui.py
```

**TUI Features:**
- Navigate between Categories, Sources, and Transactions screens
- Create, edit, and delete records interactively
- View source balances
- Jalali date picker for transactions
- Keyboard shortcuts for quick navigation

**Keyboard Shortcuts:**
- `c` - Categories screen
- `s` - Sources screen
- `t` - Transactions screen
- `q` - Quit application
- `n` - New record
- `e` - Edit selected record
- `d` - Delete selected record

## Date Format

All dates use **Jalali (Persian) calendar** in `YYYY-MM-DD` format (e.g., `1403-01-15`). The system automatically converts between Jalali and Gregorian for storage.

## Project Structure

```
terminal_accounting/
├── app.py              # Flask REST API server
├── cli.py              # Command-line interface
├── tui.py              # Terminal UI (Textual)
├── database.py         # Database initialization and connection
├── models.py           # Data validation and date conversion
├── requirements.txt    # Python dependencies
├── accounting.db       # SQLite database (auto-created)
└── README.md          # This file
```

## Development

### Running in Debug Mode

Flask debug mode is enabled by default in `app.py`:

```python
if __name__ == "__main__":
    app.run(debug=True)
```

### Database Reset

To reset the database, simply delete `accounting.db`:

```bash
rm accounting.db
```

The database will be recreated automatically on next run.

## API Examples

### Create a Category
```bash
curl -X POST http://127.0.0.1:5000/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "Salary", "type": "income"}'
```

### Create a Source with Initial Balance
```bash
curl -X POST http://127.0.0.1:5000/sources \
  -H "Content-Type: application/json" \
  -d '{"name": "Bank Sepah", "amount": 50000}'
```

### Create a Transaction
```bash
curl -X POST http://127.0.0.1:5000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "date": "1403-01-15",
    "amount": 5000,
    "category_id": 1,
    "source_id": 1,
    "description": "Monthly salary"
  }'
```

### Get Source Balance
```bash
curl http://127.0.0.1:5000/sources/1/balance
```

## License

MIT

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
