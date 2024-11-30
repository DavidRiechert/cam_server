FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopencv-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask opencv-python-headless numpy

COPY cap_cam_dev.py /app/cap_cam.py
COPY str_cam_dev.py /app/str_cam.py
COPY mot_cam_dev.py /app/mot_cam.py
COPY rec_cam_dev.py /app/rec_cam.py
COPY run.sh /app/run.sh

RUN chmod a+x /app/run.sh

WORKDIR /app

EXPOSE 5000

CMD ["./run.sh"]

