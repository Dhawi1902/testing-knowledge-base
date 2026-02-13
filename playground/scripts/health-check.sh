#!/bin/bash
# Health check script for TaskFlow backend
# Usage: ./scripts/health-check.sh

BACKEND_URL="${1:-http://taskflow.local/api/admin/health}"

echo "Checking health at $BACKEND_URL..."

response=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL")

if [ "$response" = "200" ]; then
    echo "OK - Backend is healthy"
    curl -s "$BACKEND_URL" | python3 -m json.tool 2>/dev/null || curl -s "$BACKEND_URL"
    exit 0
else
    echo "FAIL - Backend returned HTTP $response"
    exit 1
fi
