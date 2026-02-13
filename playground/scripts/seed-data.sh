#!/bin/bash
# Re-seed the database to a known state
# Usage: ./scripts/seed-data.sh

SEED_URL="${1:-http://taskflow.local/api/admin/seed}"

echo "Re-seeding database at $SEED_URL..."

response=$(curl -s -X POST "$SEED_URL")
http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$SEED_URL")

if [ "$http_code" = "200" ]; then
    echo "OK - Database re-seeded"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo "FAIL - Seed returned HTTP $http_code"
    echo "$response"
    exit 1
fi
