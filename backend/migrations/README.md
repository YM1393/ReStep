# Database Migrations

## PostgreSQL Setup

### 1. Create the database

```bash
createdb tenm_wt
```

### 2. Run the initial migration

```bash
psql -d tenm_wt -f migrations/001_initial_schema.sql
```

### 3. Configure environment variables

Set the following in your `.env` file or environment:

```
DB_TYPE=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tenm_wt
DB_USER=postgres
DB_PASSWORD=your_password
```

### 4. (Optional) Redis caching

```
REDIS_URL=redis://localhost:6379/0
```

## SQLite (default)

No migration needed. Tables are created automatically on startup when `DB_TYPE=sqlite` (or unset).

## Switching between backends

The application uses `DB_TYPE` to select the database backend:

- `DB_TYPE=sqlite` (default) - uses SQLite file at `backend/database.db`
- `DB_TYPE=postgres` - uses PostgreSQL via psycopg2

All database operations share the same interface, so switching is transparent to the rest of the application.
