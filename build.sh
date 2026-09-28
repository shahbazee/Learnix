#!/usr/bin/env bash
# Exit immediately on any error
set -o errexit

echo "=== Learnix Build: Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Learnix Build: Collecting static files ==="
python manage.py collectstatic --no-input --clear

echo "=== Learnix Build: Running database migrations ==="
python manage.py migrate --no-input

echo "=== Learnix Build: Running system checks ==="
python manage.py check --deploy 2>&1 | grep -v "WARNINGS" || true

echo "=== Learnix Build: Complete ==="
