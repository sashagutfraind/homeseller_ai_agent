#!/bin/bash

# Frontend Build Script for Real Estate Pricing Advisor

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_status "Building frontend application..."

cd frontend

# Install dependencies if needed
if [[ ! -d "node_modules" ]]; then
    print_status "Installing dependencies..."
    pnpm install
fi

# Build the frontend
print_status "Running build..."
pnpm run build

cd ..

print_success "Frontend build completed successfully!"
print_status "Build output is in frontend/dist/"
