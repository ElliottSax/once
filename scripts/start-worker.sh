#!/bin/bash
#
# Startup script for Temporal worker service
# Waits for dependencies and starts the workflow worker
#

set -e  # Exit on error

echo "====================================="
echo "Video Generation Worker Startup"
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

# Wait for Temporal server to be ready
echo "Waiting for Temporal server to be ready..."
retry_count=0

until  nc -z localhost 7233 2>/dev/null; do
  retry_count=$((retry_count + 1))
  if [ $retry_count -ge $max_retries ]; then
    echo "ERROR: Temporal server not available after $max_retries attempts"
    exit 1
  fi
  echo "Temporal not ready yet (attempt $retry_count/$max_retries)..."
  sleep 2
done

echo "Temporal server is ready!"

# Start worker
echo "Starting Temporal worker..."
exec python -m src.workflows.worker
