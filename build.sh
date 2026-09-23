#!/usr/bin/env bash
# Build script used by Render (or any Linux host). Runs on every deploy.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
