#!/bin/bash
# entrypoint.sh

# Wait for the database service to be healthy (optional, but recommended)
# You might use a dedicated script like 'wait-for-it.sh' for robustness
# Example using simple logic (from source 0.4.1):
echo "Waiting for database..."
# Add a script or logic here to ensure DB connectivity

# Run database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Start the main application process (e.g., Gunicorn or runserver)
echo "Starting application..."
exec "$@"
