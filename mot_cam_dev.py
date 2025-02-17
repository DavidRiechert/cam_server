import os
from multiprocessing import shared_memory
import cv2
import numpy as np
import time
import logging
import sys


# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# Constants
WIDTH = int(os.environ.get("WIDTH", 896))
HEIGHT = int(os.environ.get("HEIGHT", 512))
IMAGE_QUALITY = int(os.environ.get("IMAGE_QUALITY", 60))
FPS = int(os.environ.get("FPS", 10))
FRAME_SIZE = WIDTH * HEIGHT * 3  # BGR format
FRAME_INTERVAL = 1 / FPS
MOTION_THRESHOLD = int(os.environ.get("MOTION_THRESHOLD", 5000))
POST_MOTION_LENGTH = int(os.environ.get("POST_MOTION_LENGTH", 5))
MOTION_DETECTION_INTERVAL = FRAME_INTERVAL * 3


# Attach to shared Memory, this script is the producer
SHARED_MEMORY_NAME = os.environ.get("SHARED_MEMORY_NAME", "camera_shm")

# Attach to shared memory as consumer
try:
    shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME, create=False)
    frame_array = np.ndarray((HEIGHT, WIDTH, 3), dtype=np.uint8, buffer=shm.buf[:FRAME_SIZE])
    RECORDING_FLAG = np.ndarray((1,), dtype=np.uint8, buffer=shm.buf[FRAME_SIZE:])
    RECORDING_FLAG[0] = 0
    logging.info("mot_cam successfully attached to shared memory")
except FileNotFoundError:
    logging.warning(f"Shared memory {SHARED_MEMORY_NAME} not found for mot_cam. Retrying in 1 second...")
    time.sleep(1)


def detect_motion():

    time.sleep(5)

    last_motion_time = None
    prev_frame = None

    while True:
        # Ensure the frame_array contains data by checking its length
        if len(frame_array) > 0:  # Optional: You can also check specific elements
            try:
                frame = frame_array.copy()  # Copy the frame to avoid race conditions

                # Example check: Ensure the frame isn't all zeros
                if np.any(frame):  # Frame contains non-zero data
                    current_frame = frame

                    # Convert to grayscale and blur for motion detection
                    gray_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
                    gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

                    # Skip processing if no previous frame is available
                    if prev_frame is None:
                        logging.info("No previous frame")
                        prev_frame = gray_frame
                        continue

                    # Compute the difference between the current and previous frames
                    frame_diff = cv2.absdiff(prev_frame, gray_frame)
                    _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
                    motion_area = cv2.countNonZero(thresh)

                    logging.info(motion_area)
                    logging.info(MOTION_THRESHOLD)
                    logging.info(RECORDING_FLAG[0])

                    # Check for motion
                    if motion_area > MOTION_THRESHOLD:
                        last_motion_time = time.time()
                        if not RECORDING_FLAG[0] == 1:
                            logging.info("Motion detected! Starting recording ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                            RECORDING_FLAG[0] = 1

                    # Update previous frame
                    prev_frame = gray_frame
                    logging.info("Frame processed for motion detection.")
                else:
                    logging.warning("Frame contains no data. Skipping frame.")
                    
            except Exception as e:
                logging.error(f"Error processing frame: {e}")
                continue

        else:
            logging.info("Frame buffer is empty. Waiting for frames...")

        # Check if recording should stop
        if RECORDING_FLAG[0] == 1 and time.time() - last_motion_time > POST_MOTION_LENGTH:
            logging.info("Motion ended. Stopping recording -------------------------------------------------------------------------------------------")
            RECORDING_FLAG[0] = 0

        logging.info(RECORDING_FLAG[0])
        logging.info(time.time())
        logging.info(last_motion_time)
        logging.info(POST_MOTION_LENGTH)

        # Sleep for the frame interval to control loop frequency
        time.sleep(MOTION_DETECTION_INTERVAL)


if __name__ == "__main__":
    logging.info("Start motion detection main")
    try:
        detect_motion()
    except Exception as e:
        logging.error(f"An error occurred in detecting motion: {e}")
        sys.exit(1)
