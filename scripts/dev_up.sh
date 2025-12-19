#!/bin/bash
# Start development infrastructure

echo "Checking if Docker services are already running..."
# Check if at least one container from docker-compose is running
if docker-compose ps --services --filter "status=running" | grep -q .; then
    echo "Docker services are already running."
else
    echo "Starting Docker services..."
    docker-compose up -d
    echo "Waiting for services to be ready..."
    # Simple wait (could be improved with healthchecks)
    sleep 5
    echo "Services are up."
fi

