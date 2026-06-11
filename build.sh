#!/usr/bin/env bash
set -o errexit

echo "==> Checking pre-installed GDAL..."
gdal-config --version
GDAL_VERSION=$(gdal-config --version)
echo "    Found GDAL $GDAL_VERSION"

echo "==> Installing Python GDAL matching system version..."
pip install GDAL==$GDAL_VERSION

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running migrations..."
python manage.py migrate

echo "==> Build complete."