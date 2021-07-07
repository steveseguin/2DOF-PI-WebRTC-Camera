# 2DOF-PI-WebRTC-Camera

This repository contais the code for a remote contolled two degrees of freedoom streaming camera using a raspberry pi and WebRTC. Streams can be access from anywhere and generally will not require any firewall ports to be opened. 

The concpet is based on using WebRTC, specificlly on the work from vdo.ninja (formerly obs.ninja) by Steve Seguin. For more informtion on vdo.ninja see https://vdo.ninja/.

## Bill of Materials

The realize this project, you will need:
 - Raspberry Pi4 2GB or better
 - 2 x SG90s or MG90s micro servos. I generally use [MG90s six pack](https://www.amazon.com/gp/product/B07F7VJQL5/ref=ox_sc_act_title_1?smid=A1NOQTMMT39TJ0&psc=1).
 - Adafruit [PCA9865 Servo Controller Hat](https://www.amazon.com/gp/product/B00SI1SPHS/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1)
 - LattePanda [5MP USB Autofocus Camera](https://www.amazon.com/gp/product/B082SKDTXZ/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1).While this is not the greatest camera, I chose it for its auto-focus capability, which works reasonable well. It comes with a fairly long cable, which should be shortened to about 6 inches. 
 - [Suction Cup Mount](https://www.amazon.com/gp/product/B07W7H121C/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1) to mount the assembly
 - 3D Printed parts at [tbd](http://8.8.8.8)

## Camera Streaming Container

The actual streaming is performed via dockerized container utilizing gstreamer and a custom python wrapper to perform the registration and handshake with WebRTC peers. 

The python code is in ```obscam->app``` folder. The obscam folder also contains the Dockerfiles to build the docker containers. For ease, you can pull the compiled container:
```
    docker pull innovationcontainerimages.azurecr.io/obs-cam:pi
```
if you do not want to use the containerized approach, you can build the support for gstreamer using the build scripts contains in the ```obscam -> scripts``` folder.

After pulling the container, please update the envrionment file (```obscam -> env_file```) for your situation. You will want to adjust specifically:

- ```CAM_SOURCE``` - choose between ```rpi_cam```, ```v4l2src``` and ```test```. Use ```v4lsrc``` for any usb cam, ```rpi_cam``` if you have attached a camera to the PI camera interface and ```test``` for an internal test source (a good option for troubleshooting)
- ```STREAM_ID``` - the id of your stream. Choose a unique identifier. You will use this id to access the stream remotely. 
- ```WIDTH```/```HEIGHT```/```FPS``` - enter values supported by your camera. If you use the camera from the BOM above, you will not need to adjust this. 
- ```CAM_SOURCE_PARAMS``` - enter the device representing the camera. Generally, you will not need to change that. 
- ```CAPS``` - the caps used for the gstreamer pipeline. Only adjust this if you know what your doing. The caps need to be supported by your camera. 

After that, you can start the container using 

```
docker run -d --network host --privileged --env-file env_file --device /dev/vchiq --device /dev/video0 --name obs-cam obs-cam:pi
```
If you prefer to run outside the container, you can start the server using 
```
python3 app/server.py --help
python3 app/server.py [options]
``` 

Currently, the streaming supports only one client at the time. 

## Servo Controller Container

The servo controller controls the direction and elevation of the camera plane. For convenience, it is packages as a container. 