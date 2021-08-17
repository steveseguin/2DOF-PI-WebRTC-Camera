``` This is still work in progress ```

# 2DOF-PI-WebRTC-Camera

This repository contais the code for a remote contolled two degrees of freedoom (pan and title) streaming camera using a raspberry pi and WebRTC. Streams can be access from anywhere and generally will not require any firewall ports to be opened. 

The concpet is based on using WebRTC, specificlly on the work from vdo.ninja (formerly obs.ninja) by Steve Seguin. For more informtion on vdo.ninja see https://vdo.ninja/.

The camera is intended to be controlled and managed through Azure IoT Hub or Azure IoT Central. 

## Architectural Overview

[TBD]

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

The python code is in ```modules->obscam->app``` folder. The obscam folder also contains the Dockerfiles to build the docker containers. For ease, you can pull the compiled container:
```
    docker pull innovationcontainerimages.azurecr.io/obs-cam:streamer-pi
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
python3 app/app.py --help
python3 app/app.py [options]
``` 

The streaming supports multiple clients up to a configurable limnit (albeit, client dropoff detection is a bit wonky at the moment, needs work to avoid runaway pipelines)

## Servo Controller Container

The servo controller controls the direction and elevation of the camera plane. For convenience, it is packaged as a container. The servos are attached to a PCA9685 based servo hat. 

The coode for the controller is in ```modules->controller->app```. The controller supports 4 methods:

- PanTo - pans the camera to a certain angle, with 0 being netural.
- PanBy - pans the camera by an angle from the current orientation. 
- TiltTo - tilts the camera to a certain elevation, with 0 being neutral
- TiltBy - tilts the camera by a certain angle from the current elevation. 

The contoller is deployed as a containerized workfload and is intended to be managed through IoT Central or IoT Hub. The container workload is deployed using the IoTHub deployment manifest when the client device connects to the hub. 

## Device Infomation Container

The device information container provides some telemetry of the device running the workfloads to enable remote monitoring. The code for the device information workload is in ```modules->device->app```. The device information workload also provides remote shutdown and reboot methods. 

## Deployment to Azure IoT Hub or IoT Central

<div style="float:right">
<img src="https://github.com/Avanade/2DOF-PI-WebRTC-Camera/blob/master/images/WebRTC%20Camera%20-%20Camera.png?raw=true" align="right" width="400" height="300" style="max-width:400px; float: right;padding: 20px 0px 20px 20px"/>
</div>

The workloads support both IoT Hub and IoT Central. For deployment to IoT Hub, only the deployment manifest ```obs-cam.device.manifest.json``` is required. There are plenty tutorials but in a nutshell:

- In Azure IoTHub:
    - Create a new deployment. Match it to the desired device ids. 
    - Import the manifest to define the workloads. 
    - Create a device with a matching device id. 

- On the device:
    - Install Azure IoT Edge
    - Update the IoT Edge configuration to connect to your IoT Hub. 

<div style="float:right">
<img src="https://github.com/Avanade/2DOF-PI-WebRTC-Camera/blob/master/images/WebRTC%20Camera%20-%20Device%20Information.png?raw=true" align="right" width="400" height="300" style="max-width:400px; float: right;padding: 20px 0px 20px 20px"/>
</div>

Azure IoT will pull the containers and deploy the workloads on your device. Everything is then configurable using the module twins for the various modules. You can invoke the methods defined through the hub as well. 

If you use IoTCentral instead of IoT Hub (IoTCentral uses IoT Hub under the hood), you will get a consumer user interface also. In that case, replace the IoT Hub steps as follows:

- In IoT Central, create a new device template for the Edge Device. 
- Use the ```obs-cam.device.manifest.json``` as the manifest for the edge device. 
- Import the additional module property and telemetry interfaces:
    - ```device.controller.json``` for the Module Controller
    - ```device.information.json``` for the Module Device Information
    - ```camera.telemetry.json``` for the Module Camera
- Create Dashboards as desired. See below for some example dashbaords. Unfortunately, they are not exportable, but they can be easily created. 
- Publish your device template. 
- Create a device. Use the device connection info to connfigure Azure IoT Edge on the device. 

## Consuming the Camera Feed

<div style="float:right">
<img src="https://github.com/Avanade/2DOF-PI-WebRTC-Camera/blob/master/images/WebRTC%20Camera%20-%20Feed.png?raw=true" align="right" width="400" style="max-width:400px; float: right;padding: 20px 0px 20px 20px"/>
</div>
 
The url to the exported feed (using vdo.ninja) is avaialbe in both the device twin and the device telemetry. In the images above, I included the link on the dashboard for the camera. You can use that link in the browser or incorporate it into your OBS scence(s). 
