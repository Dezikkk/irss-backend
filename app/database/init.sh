#!/bin/bash
user=postgres
# Before running this script, create the database:
# psql -U youruser -c "CREATE DATABASE zapisy_backend;"
#
for f in schema/*.sql; do
    echo "Running $f..."
    psql -U $user -d zapisy_backend -f "$f"
done
