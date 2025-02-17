# cam_server

Dedicated camera server for IP cameras supporting the RTSP protocol

    git clone https://github.com/DavidRiechert/cam_server.git

In case git is not installed on your host device, you can install it with the following command:

    sudo apt install git

after getting this repository be sure to navigate into the cam_server directory
  
  build the docker image with:
  
    docker build -t cam_server .
    
  this may take serveral minutes as docker gets the latest (3.11) python image, although the slim version...
  
  run each camera in a dedicated container with:
  
    docker run -d --rm --shm-size=512m --privileged -e CAMERA_RTSP_URL="rtsp://username:password@<camera_ip>/<camera_video_feed>" -e CAMERA_NAME="<your_camera_name>" -e SHARED_MEMORY_NAME="<your_shared_memory_name>" -p <your_port>:5000 -v /path/to/your/recordings:/recordings cam_server
  
# each flag explained:
  
  -d: Optional: runs the container detached from your terminal session
  
  --rm: Optional: container is deleted automatically after stopped with $ docker stop <container_id/container_name> 
  
  --shm-size: Required: defines the actual space in MB for the shared memory (512m reserves 512MB of memory on your devices) 

  --privileged: Required: allows for direct communication with host device hardware e.g. /video/video0
  
  -e CAMERA_RTSP_URL: Required: rtsp url to your IP camera in your network, be sure to setup an account on the camera with username:password (check camera manufacturer specs) 
  
  -e CAMERA_NAME: Optional: name your camera for ease of reference in the recording file naming
  
  -e SHARED_MEMORY_NAME: Optional: name the shared memory to avoid leaks, especially when running multiple cameras on the same device 
  
  -p <your_port>:5000: Required: the container exposes port:5000, map your desired port to access the live stream in the browser 
  
  -v /path/to/your/recordings:/recordings: Required: mounts a drive to the internal /recordings directory, provide a path on your device to access recordings

  cam_server: name of the image that you build, check availability of image with $ docker images

  
Once a contaiiner is running on your device, open a browser tab and navigate to http://device_ip:your_port and the live stram of your camera will appear

all recordings can be found in the ./recordings sub_directory of your current directory

Enjoy!!!

# environment variables:

Environment variables can be set when running the container in the same way we have seen in the docker run command before. Simple put -e "VARIABLE_NAME" for each variable. Below is a comprehensive list of all possible variables and its default values:

WIDTH = int(os.environ.get("WIDTH", 896))

HEIGHT = int(os.environ.get("HEIGHT", 512))

IMAGE_QUALITY = int(os.environ.get("IMAGE_QUALITY", 60))

FPS = int(os.environ.get("FPS", 10))

PRE_MOTION_LENGTH = int(os.environ.get("PRE_MOTION_LENGTH", 10))

CAMERA_NAME = os.environ.get("CAMERA_NAME", "camera_001")

LOCAL_TIMEZONE = os.environ.get("LOCAL_TIMEZONE", "Europe/Stockholm")

MOTION_THRESHOLD = int(os.environ.get("MOTION_THRESHOLD", 5000))

POST_MOTION_LENGTH = int(os.environ.get("POST_MOTION_LENGTH", 5))



# Shared Memory

  The size of the shared memory depends on several factors. The default frame rate is set to 10 FPS and the image frame size is set to 896 * 512 pixel. The size of one frame is 896 * 512 * 3 (BGR format) = 1376256 byte => 1,376 MB. At 10 FPS one second of stream buffering takes 13,76 MB of the shared memory. The default buffering of a live stream is set to 10 seconds, which requires 137,6 MB (13,76 MB/second * 10 seconds) of the shared memory. Be sure to cater for sufficient memory size when changing the frame size of frames per second.


# Docker

  In order to build the image you need docker to be installed and enabled on your device. In case docker is not installed, take the following steps.

  Update and Upgrade

    sudo apt update
    sudo apt upgrade

  Install Docker
    
    sudo apt install docker.io

  Enable the service
  
    sudo systemctl enable docker.service

  Start the service
    
    sudo systemctl start docker.service

  Check the status
  
    sudo systemctl status docker.service

  Setup your user
  
    sudo usermod -a -G docker <your_username>

    id <your_username>

    newgrp docker
