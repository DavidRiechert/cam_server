# cam_server

Dedicated camera server for IP cameras supporting the RTSP protocol

after getting this repository:

be sure to navigate into the cam_server directory

build the docker image with:

docker build -t cam_server .

this may take serveral minutes as docker gets the latest (3.11) python image, although the slim version...
run each camera in a dedicated container with:

docker run -d --rm --shm-size=512m --privileged -e CAMERA_RTSP_URL="rtsp://:@<camera_ip>/<camera_video_feed>" -e CAMERA_NAME="<your_camera_name>" -e SHARED_MEMORY_NAME="<your_shared_memory_name>" -p <your_port>:5000 -v /path/to/your/recordings:/recordings cam_server

each flag explained:

-d: runs the container detached from console --rm: container is deleted after stopped --shm-size: defines the actual space in MB for the shared memory -e CAMERA_RTSP_URL: rtsp url to your ip camera in your network (check manufacturer specs) -e CAMERA_NAME: Optional: name your camera for ease of reference in the recording file naming -e SHARED_MEMORY_NAME: Optional: name the shared memory to avoid leaks, especially when running multiple cameras on the same device -p the container exposes port:5000, map your desired port to access via broser -v mount a drive to the internal /recordings directory

On a device on the same network, in a broser, navigate to your hosting device_ip:your_port and the live stram of your camera will appear

all recordings can be found in the ./recordings sub_directory of your current directory

Enjoy!!!
