#!/bin/bash

#Service to capture image frames
echo "Starting cap_cam.py..."
python3 /app/cap_cam.py &

#Waiting for shared memory to be initialized since all other services require this memory instance
while [ ! -f /tmp/shm_ready ]; do
    echo "Waiting for cap_cam to initialize shared memory..."
    sleep 0.1
done

#Service to stream the captured images to internal port:5000 and make it accessible direclty in the browser
echo "Starting str_cam.py..."
python3 /app/str_cam.py &

#Service to detect motion through image frame comparison, handling logic for pre-motion and post-motion buffering
echo "Starting mot_cam.py..."
python3 /app/mot_cam.py &

#Service to record live frames after motion detection, handling logic to append pre-motion and post-motion frames
echo "Starting rec_cam.py..."
python3 /app/rec_cam.py &

echo "All scripts started. Waiting for processes..."
wait
