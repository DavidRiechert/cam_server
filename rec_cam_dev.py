import os
from multiprocessing import shared_memory
import numpy as np
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import sys


# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# Constants
WIDTH = int(os.environ.get("WIDTH", 896))
HEIGHT = int(os.environ.get("HEIGHT", 512))
FPS = int(os.environ.get("FPS", 10))
FRAME_SIZE = WIDTH * HEIGHT * 3  # BGR format
FRAME_INTERVAL = 1 / FPS
PRE_MOTION_LENGTH = int(os.environ.get("PRE_MOTION_LENGTH", 10)) # seconds before first motion is detected
BUFFER_SIZE = FPS * PRE_MOTION_LENGTH
CAMERA_NAME = os.environ.get("CAMERA_NAME", "camera_001")
LOCAL_TIMEZONE = os.environ.get("LOCAL_TIMEZONE", "Europe/Stockholm")
RECORD_PATH = "/recordings"
os.makedirs(RECORD_PATH, exist_ok=True)


# Setup Shared Memory, this script is the producer
SHARED_MEMORY_NAME = os.environ.get("SHARED_MEMORY_NAME", "camera_shm")

try:
    shm = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME, create=False)
    frame_array = np.ndarray((HEIGHT, WIDTH, 3), dtype=np.uint8, buffer=shm.buf[:FRAME_SIZE])
    RECORDING_FLAG = np.ndarray((1,), dtype=np.uint8, buffer=shm.buf[FRAME_SIZE:])
    frame_buffer = np.ndarray((BUFFER_SIZE, HEIGHT, WIDTH, 3), dtype=np.uint8, buffer=shm.buf[FRAME_SIZE + 1:])
    last_write_index = np.ndarray((1,), dtype=np.uint8, buffer=shm.buf[FRAME_SIZE + 1 + BUFFER_SIZE:])
    logging.info("rec_cam successfully attached to shared memory")
except FileNotFoundError:
    logging.warning(f"Shared memory {SHARED_MEMORY_NAME} not found for rec_cam. Retrying in 1 second...")
    time.sleep(1)
logging.info(f"frame array length: {len(frame_array)}")


def save_video():
    """Save video using FFmpeg."""

    while True:
        logging.info("recording_flag below:")
        logging.info(RECORDING_FLAG[0])
        if RECORDING_FLAG[0] == 1:

            # Start FFmpeg process for recording
            local_timezone = ZoneInfo(LOCAL_TIMEZONE)
            timestamp = datetime.now(local_timezone).strftime("%Y-%m-%d_%H-%M-%S")
            output_file = f"{RECORD_PATH}/{CAMERA_NAME}_{timestamp}.mp4"

            # FFmpeg command
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-f", "rawvideo",
                "-pixel_format", "bgr24",
                "-video_size", f"{WIDTH}x{HEIGHT}",
                "-framerate", str(FPS),
                "-i", "-",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_file
            ]

            logging.info(f"Starting FFmpeg process for {output_file}")
            process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

            try:

                frame_count = 0
                last_written_frame = None
                all_frames = []

                while RECORDING_FLAG[0] == 1:

                    logging.info("recording in progress.....................................................................................................")
                    if len(frame_array) > 0:
                        current_frame = frame_array.copy()
                        if not np.array_equal(current_frame, last_written_frame):

                            if frame_count == 0:
                                latest_write_index = last_write_index[0]
                                logging.info("start pre motion frame handling")
                                logging.info(f"first last_write_index: {last_write_index[0]}")
                                latest_frames = [frame.copy() for frame in frame_buffer[0:latest_write_index]]
                                if last_write_index[0] < BUFFER_SIZE - 1:
                                    oldest_frames = [frame.copy() for frame in frame_buffer[last_write_index[0] + 1:BUFFER_SIZE]]
                                else:
                                    oldest_frames = []
                                all_frames.extend(oldest_frames + latest_frames)
                                logging.info(f"Pre-motion frames added: {len(all_frames)}")

                            if len(all_frames) == 0 or not np.array_equal(current_frame, all_frames[-1]):
                                all_frames.append(current_frame.copy())
                                logging.info(f"Appended live frame {frame_count} @ last_write_index: {last_write_index[0]} to all_frames.")


                            logging.info(f"write live frame: {time.time()}")
                            last_written_frame = current_frame
                            frame_count += 1
                            logging.info(f"Writing frame {frame_count} at {time.time():.2f}")

                    time.sleep(FRAME_INTERVAL)


                logging.info(f"writing frames: {time.time()}")
                for frame in all_frames:
                    process.stdin.write(frame.tobytes())
                    process.stdin.flush()

                logging.info("Finalizing recording...")

                process.stdin.close()
                process.wait()

                if process.returncode != 0:
                    logging.info(f"FFmpeg error: {process.stderr.read().decode()}")
                else:
                    logging.info(f"Recording saved to {output_file}")

            except Exception as e:
                logging.info(f"Error during FFmpeg execution: {e}")
                process.terminate()
            finally:
                process.stdin.close()
                process.wait()

        else:
            logging.info("no recording!!!")

        time.sleep(FRAME_INTERVAL)


if __name__ == "__main__":
    logging.info("Start recording main")
    try:
        save_video()
    except Exception as e:
        logging.error(f"An error occurred starting recording: {e}")
        sys.exit(1)
