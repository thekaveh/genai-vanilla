#!/bin/bash

# This script installs and enables pgvector and postgis extensions

set -e

echo "Setting up PostgreSQL extensions..."

# Setup pgvector extension
echo "Installing pgvector..."
cd /tmp

# Install build dependencies
apt-get update
apt-get install -y \
    build-essential \
    postgresql-server-dev-16 \
    git \
    wget \
    cmake

# Clone and build pgvector
git clone --branch v0.6.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Setup PostGIS (already available in postgres-16 container with appropriate extensions)
echo "Installing PostGIS..."
apt-get install -y \
    postgis \
    postgresql-16-postgis-3

echo "Extensions installed successfully."

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*
