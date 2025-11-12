#!/bin/bash
#
# Startup script for API service
# Runs database migrations and starts the FastAPI server
#

set -e  # Exit on error

echo "====================================="
echo "Video Generation API Startup"
echo "====================================="

# Wait for database to be ready
echo "Waiting for database to be ready..."
max_retries=30
retry_count=0

until psql "$DATABASE_URL" -c '\q' 2>/dev/null; do
  retry_count=$((retry_count + 1))
  if [ $retry_count -ge $max_retries ]; then
    echo "ERROR: Database not available after $max_retries attempts"
    exit 1
  fi
  echo "Database not ready yet (attempt $retry_count/$max_retries)..."
  sleep 2
done

echo "Database is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully!"

# Start API server
echo "Starting API server on port 8000..."
exec uvicorn src.api.main_db:app --host 0.0.0.0 --port 8000
