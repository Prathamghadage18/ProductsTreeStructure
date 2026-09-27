#!/bin/bash

# Health check script for Docker container
# This script checks if the Django application is responding

set -e

# Configuration
MAX_RETRIES=30
RETRY_INTERVAL=2
HEALTH_URL="http://localhost:8000/health/"

echo "Starting health check for Django application..."

# Wait for application to start
for i in $(seq 1 $MAX_RETRIES); do
    if curl -f -s -o /dev/null "$HEALTH_URL"; then
        echo "✓ Application is healthy and responding"
        exit 0
    else
        echo "Attempt $i/$MAX_RETRIES: Application not ready yet, waiting..."
        sleep $RETRY_INTERVAL
    fi
done

echo "✗ Health check failed after $MAX_RETRIES attempts"
exit 1
