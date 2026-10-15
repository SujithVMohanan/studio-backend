#!/bin/sh
set -e

if [ "$1" = "serve" ]; then
    echo "Applying migrations..."
    python manage.py migrate --noinput

    echo "Loading demo data..."
    python manage.py seed_demo

    echo "Starting the API on port 8000..."
    exec python manage.py runserver 0.0.0.0:8000
fi

exec "$@"
