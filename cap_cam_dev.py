import os
from multiprocessing import shared_memory
import subprocess
import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import shutil
import signal
import logging
import sys


# Logging Config
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# Constants
CAMERA_RTSP_URL = os.environ.get("CAMERA_RTSP_URL")
WIDTH = int(os.environ.get("WIDTH", 896))
HEIGHT = int(os.environ.get("HEIGHT", 512))
FPS = int(os.environ.get("FPS", 10))
PRE_MOTION_LENGTH = int(os.environ.get("PRE_MOTION_LENGTH ", 10)) # seconds before first motion is detected
FRAME_SIZE = WIDTH * HEIGHT * 3  # BGR format
FRAME_INTERVAL = 1 / FPS
BUFFER_SIZE = FPS * PRE_MOTION_LENGTH
LOCAL_TIMEZONE = os.environ.get("LOCAL_TIMEZONE", "Europe/Stockholm")
RECORD_PATH = "/recordings"


# Setup Shared Memory, this script is the producer
SHARED_MEMORY_NAME = os.environ.get("SHARED_MEMORY_NAME", "camera_shm")
SHARED_MEMORY_SIZE = FRAME_SIZE * FPS * PRE_MOTION_LENGTH * 2

try:
    shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME, create=True, size=SHARED_MEMORY_SIZE)
    frame_array = np.ndarray((HEIGHT, WIDTH, 3), dtype=np.uint8, buffer=shm.buf[:FRAME_SIZE])
    frame_buffer = np.ndarray((BUFFER_SIZE, HEIGHT, WIDTH, 3), dtype=np.uint8, buffer=shm.buf[FRAME_SIZE + 1:])
    last_write_index = np.ndarray((1,), dtype=np.uint8, buffer=shm.buf[FRAME_SIZE + 1 + BUFFER_SIZE:])
    with open("/tmp/shm_ready", "w") as f:
        f.write("ready")
    logging.info("Shared memory initialized and ready!")
except Exception as e:
    logging.error(f"Failed to create shared memory: {e}")
    sys.exit(1)


# Flag to control graceful shutdown
running = True

# Setting local timezone
local_timezone = ZoneInfo(LOCAL_TIMEZONE)


def signal_handler(sig, frame):
    """Handle termination signals (e.g., Ctrl+C)."""
    global running
    logging.info("Shutting down capture process...")
    running = False


def move_recordings():
    # Ensure the destination folder exists

    previous_date = (datetime.now(local_timezone) - timedelta(days=1)).strftime("%Y-%m-%d")
    destination_folder = f"/recordings/{previous_date}"

    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)

    # Iterate through all files in the source folder
    for filename in os.listdir(RECORD_PATH):
        source_path = os.path.join(RECORD_PATH, filename)
        destination_path = os.path.join(destination_folder, filename)

        # Only move files (skip directories)
        if os.path.isfile(source_path):

            if previous_date in filename:
                file_size = os.path.getsize(source_path) / (1024 * 1024)  # Convert bytes to MB

                # Construct the new filename with size appended
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_{file_size:.2f}MB{ext}"
                destination_path = os.path.join(destination_folder, new_filename)

                shutil.move(source_path, destination_path)
                logging.info(f"Moved: {source_path} -> {destination_path}")


def capture_frames():
    """Capture frames from an RTSP stream and write them to shared memory."""
    logging.info("Starting frame capture...")

    ffmpeg_cmd = [
        'ffmpeg',
        '-hwaccel', 'v4l2', # Enable hardware acceleration
        '-rtsp_transport', 'tcp',
        '-stimeout', '5000000', # Timeout after 5 seconds (in microseconds)
        '-reconnect', '1', # Enable reconnection
        '-reconnect_at_eof', '1', # Reconnect if the end of file is reached
        '-reconnect_streamed', '1', 
        '-i', CAMERA_RTSP_URL,
        '-an', # Disable audio processing
        #'-vf', f'scale={WIDTH}:{HEIGHT}',
        '-r', f'{FPS}',
        '-q:v', '31',
        '-pix_fmt', 'bgr24',
        '-vcodec', 'rawvideo',
        #'-f', 'mjpeg',
        '-f', 'rawvideo',
        '-fflags', 'nobuffer',
        '-flags', 'low_delay',
        '-avioflags', 'direct',
        '-timeout', '300000',
        '-'
    ]

    # Launch the FFmpeg process
    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    write_index = 0
    
    while True:
        try:

            if process.poll() is not None:  # Check if the process is terminated
                logging.warning("Process terminated. Restarting...")
                process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                continue
            
            # Read raw frame data (WIDTH * HEIGHT * 3 for BGR format)
            raw_frame = process.stdout.read(WIDTH * HEIGHT * 3)
           
            # Check if the frame is complete
            if len(raw_frame) != WIDTH * HEIGHT * 3:
                logging.warning("Incomplete frame received. Skipping this frame.")
                continue  # Skip to the next iteration

            # Convert the raw bytes into a numpy array (frame)
            frame = np.frombuffer(raw_frame, np.uint8).reshape((HEIGHT, WIDTH, 3))

            # Write frame to shared memory
            frame_array[:] = frame
            logging.info("Frame written to shared memory.")

            # Write the frame to the circular buffer
            frame_buffer[write_index] = frame
            logging.info(f"Frame written to buffer at index {write_index}")
            last_write_index[0] = write_index
            write_index = (write_index + 1) % BUFFER_SIZE

            current_time = datetime.now(local_timezone)
            if current_time.hour == 3 and current_time.minute == 0:
                move_recordings()
                continue

        except Exception as e:
            logging.error(f"Error during frame processing: {e}")
            continue

        stderr_output = process.stderr.read(1024)
        if stderr_output:
            logging.error(stderr_output.decode())
            continue
        
        # Sleep to reduce CPU usage
        time.sleep(FRAME_INTERVAL)

    # Clean up resources on shutdown
    logging.info("Releasing resources...")
    shm.close()
    shm.unlink()
    logging.info("Capture process terminated.")


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        capture_frames()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)
