#!/usr/bin/env bash
set -e

echo "=== Starting ReStep API ==="
echo "DB_TYPE=$DB_TYPE"
echo "DB_HOST=$DB_HOST"
echo "DATABASE_URL is set: $([ -n "$DATABASE_URL" ] && echo YES || echo NO)"

echo "=== Initializing database ==="
python -c "
from app.models.db_factory import init_db, DB_TYPE
print(f'DB_TYPE={DB_TYPE}')
init_db()
print('DB initialized OK')
"

echo "=== Starting uvicorn ==="
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
