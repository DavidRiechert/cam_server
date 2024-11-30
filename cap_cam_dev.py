import os
from multiprocessing import shared_memory
import subprocess
import cv2
import numpy as np
import time
import signal
import logging
import sys


# Logging Config
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# Constants
CAMERA_RTSP_URL = os.environ.get("CAMERA_RTSP_URL")
WIDTH, HEIGHT = 896, 512
FPS = os.environ.get("FPS", 10)
PRE_MOTION_LENGTH = os.environ.get("PRE_MOTION_LENGTH ", 10) # seconds before first motion is detected
FRAME_SIZE = WIDTH * HEIGHT * 3  # BGR format
FRAME_INTERVAL = 1 / FPS
BUFFER_SIZE = FPS * PRE_MOTION_LENGTH


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


def signal_handler(sig, frame):
    """Handle termination signals (e.g., Ctrl+C)."""
    global running
    logging.info("Shutting down capture process...")
    running = False


def capture_frames():
    """Capture frames from an RTSP stream and write them to shared memory."""
    logging.info("Starting frame capture...")

    ffmpeg_cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', CAMERA_RTSP_URL,
        '-vf', f'scale={WIDTH}:{HEIGHT}',
        '-r', f'{FPS}',
        '-preset', 'ultrafast',
        '-q:v', '31',
        '-pix_fmt', 'bgr24',
        '-vcodec', 'rawvideo',
        '-f', 'mjpeg',
        '-fflags', 'nobuffer',
        '-flags', 'low_delay',
        '-avioflags', 'direct',
        '-timeout', '100000',
        '-'
    ]

    # Launch the FFmpeg process
    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    write_index = 0

    while True:
        try:
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

        except Exception as e:
            logging.error(f"Error during frame processing: {e}")
            break
        
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
