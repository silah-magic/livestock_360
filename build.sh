#!/usr/bin/env bash
set -o errexit

echo "==> Installing system GDAL libraries..."
mkdir -p /var/lib/apt/lists/partial
apt-get update -qq
apt-get install -y gdal-bin libgdal-dev python3-gdal

echo "==> Detecting system GDAL version..."
GDAL_VERSION=$(gdal-config --version)
echo "    System GDAL: $GDAL_VERSION"

echo "==> Installing Python GDAL..."
pip install GDAL==$GDAL_VERSION

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running migrations..."
python manage.py migrate

echo "==> Build complete."