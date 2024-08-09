#!/bin/bash
echo "Launching baseline training. This may take some time, especially to preprocess the data"
# Trigger the appropriate dag
# First check if it is paused, if so, unpause it. Otherwise manually trigger it
# This avoid a "double run" that happens if you manually trigger a scheduled run

res=$(curl -s -X GET 'localhost:8080/api/v1/dags/baseline' --user "admin:admin" -H 'Content-Type: application/json' | jq .is_paused)
if [ "$res" = "true" ]; then
    echo "Unpaused the dag"
    curl -s -X PATCH 'localhost:8080/api/v1/dags/baseline?update_mask=is_paused' \
        -H 'Content-Type: application/json' \
        --user "admin:admin" \
        -d '{
            "is_paused": false
        }'
else
    echo "Manually triggered the dag"
    curl -s -X POST 'localhost:8080/api/v1/dags/baseline/dagRuns' -H 'Content-Type: application/json' --user "admin:admin" -d '{}' > /dev/null
fi

echo "View progress on http://localhost:8080"