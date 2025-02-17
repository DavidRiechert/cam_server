import os
from multiprocessing import shared_memory
import cv2
import numpy as np
from flask import Flask, Response
import time
import logging


# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# Flask app
app = Flask(__name__)


# Constants
WIDTH = int(os.environ.get("WIDTH", 896))
HEIGHT = int(os.environ.get("HEIGHT", 512))
IMAGE_QUALITY = int(os.environ.get("IMAGE_QUALITY", 60))
FPS = int(os.environ.get("FPS", 10))
FRAME_SIZE = WIDTH * HEIGHT * 3  # BGR format
FRAME_INTERVAL = 1 / FPS


# Attach to shared Memory, this script is the producer
SHARED_MEMORY_NAME = os.environ.get("SHARED_MEMORY_NAME", "camera_shm")

# Attach to shared memory as consumer
try:
    shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME, create=False)
    frame_array = np.ndarray((HEIGHT, WIDTH, 3), dtype=np.uint8, buffer=shm.buf[:FRAME_SIZE])
    logging.info("str_cam successfully attached to shared memory")
except FileNotFoundError:
    logging.warning(f"Shared memory {SHARED_MEMORY_NAME} not found for str_cam. Retrying in 1 second...")
    time.sleep(1)
        

def generate_frames():
    """Generate frames for streaming."""

    while True:
        frame = frame_array.copy()

        if frame is not None:
                                  
            # Encode the frame to JPEG format for streaming
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), IMAGE_QUALITY])
            frame_data = buffer.tobytes()

            # Yield the frame as a byte-stream in multipart format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
        
        logging.info(FPS)
        time.sleep(FRAME_INTERVAL)
        
    if shm is not None:
        shm.close()


@app.route('/video_feed')
def video_feed():
    """Video streaming route that returns the frame data."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    logging.info("Starting video streaming server...")
    try:
        # Run the Flask app
        app.run(host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        logging.info("Shutting down server...")
