# Copyright (c) 2021 Avanade
# Author: Thor Schueler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import sys
import os
import asyncio
import datetime
import json
import logging
import argparse
import gi

from jsonmerge import merge
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodRequest
from types import SimpleNamespace
from server import WebRTCClient

gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import Gst, GstSdp, GstWebRTC

logging.basicConfig(level=logging.DEBUG)
logging.root.setLevel(logging.INFO)
logger = logging.getLogger("htxi.modules.camera")
logger.setLevel(logging.INFO)

test_video_pipeline = '''
webrtcbin name=sendrecv bundle-policy=max-bundle
 videotestsrc ! {custom}  videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay !
 queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! sendrecv.
 audiotestsrc is-live=true wave=red-noise ! audioconvert ! audioresample ! queue ! opusenc ! rtpopuspay !
 queue ! application/x-rtp,media=audio,encoding-name=OPUS,payload=96 ! sendrecv.
''' # test source with video and audio.

rpi_cam_pipeline = '''
webrtcbin name=sendrecv bundle-policy=max-bundle
rpicamsrc bitrate=2000000 ! video/x-h264,profile=constrained-baseline,width={width},height={height},framerate={fps}/1,level=3.0 ! {custom}  queue ! h264parse ! rtph264pay config-interval=-1 !
queue ! application/x-rtp,media=video,encoding-name=H264,payload=96 ! sendrecv.
''' # raspberry pi camera needed; audio source removed to perserve simplicity.

v4l_pipeline = '''
webrtcbin name=sendrecv bundle-policy=max-bundle 
v4l2src {source_params} ! {caps} ! {custom} videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay ! queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! sendrecv.
''' # usb camera needed; audio source removed to perserve simplicity.

async def main(settings:SimpleNamespace):

    async def command_handler(request: MethodRequest):
        # Define behavior for handling commands
        try:
            if (module_client is not None):
                logger.info(f'{datetime.datetime.now()}: Received command request from IoT Central: {request.name}, {request.payload}')
                #if request.name in CommandProcessor.Commands():
                #    await CommandProcessor.Commands()[request.name](module_client, request)
                #else:
                #    raise ValueError('Unknown command', request.name)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()}: Exception during command listener: {e}")

    async def get_twin():
        twin = await module_client.get_twin()
        logger.info(f'{datetime.datetime.now()}: Received module twin from IoTC: {twin}')
        await twin_update_handler(twin['desired'])

    async def report_properties():
        propertiesToUpdate = {
            'stream_url': f'https://backup.obs.ninja/?password=false&view={settings.stream_id}'
        }
        logger.info(f'{datetime.datetime.now()}: Device properties sent to IoT Central: {propertiesToUpdate}')
        await module_client.patch_twin_reported_properties(propertiesToUpdate)
        logger.info(f'{datetime.datetime.now()}: Device properties updated.') 

    async def restart_webrtc_client():
        nonlocal webrtc_task
        if webrtc_task is not None:
            webrtc_task.cancel()
            while not webrtc_task.done():
                await asyncio.sleep(1)
            logger.info(f'{datetime.datetime.now()}: Running webrtc task cancelled. Respawn.')
            webrtc_task = asyncio.create_task(webrtc_client.loop())

    def build_gst_pipeline() -> bool:
        if settings.cam_source == 'test': settings.gst_pipeline = test_video_pipeline.format(custom=settings.custom_pipeline)
        elif settings.cam_source == 'rpi_cam': settings.gst_pipeline = rpi_cam_pipeline.format(custom=settings.custom_pipeline, width=settings.width, height=settings.height, fps=settings.fps)
        elif settings.cam_source == 'v4l2src': 
            settings.gst_pipeline = v4l_pipeline.format(caps=settings.caps, source_params=settings.cam_source_params, custom=settings.custom_pipeline)
            settings.gst_pipeline = settings.gst_pipeline.format(width=settings.width, height=settings.height, fps=settings.fps)
        else:
            return False
        return True

    async def send_telemetry():
        # Define behavior for sending telemetry
        while True:
            try:
                telemetry = {
                    "connected_clients": webrtc_client.Clients
                }
                payload = json.dumps(telemetry)
                logger.info(f'{datetime.datetime.now()}: Device telemetry: {payload}')
                await module_client.send_message(payload)  
            except Exception as e:
                logger.error(f'{datetime.datetime.now()}: Exception during sending metrics: {e}')
            finally:
                await asyncio.sleep(sampleRateInSeconds)       

    async def twin_update_handler(patch):
        nonlocal sampleRateInSeconds, settings
        logger.info(f'{datetime.datetime.now()}: Received twin update from IoT Central: {patch}')
        if 'period' in patch: sampleRateInSeconds = patch['period']
        if 'az_logging_level' in patch: logging.getLogger("azure.iot.device").setLevel(patch['az_logging_level'])
        if 'settings' in patch: 
            settings = SimpleNamespace(** merge(settings.__dict__, patch['settings']))
            if webrtc_task is not None:
                build_gst_pipeline()
                if webrtc_client.Pipeline != settings.gst_pipeline: webrtc_client.Pipeline = settings.gst_pipeline
                if 'stream_id' in patch['settings']: 
                    await report_properties()
                    webrtc_client.StreamId = settings.stream_id
                if 'server' in patch: webrtc_client.Server = settings.server
                logger.info(f"{datetime.datetime.now()}: Settings have changed, re-launching webrtc stream.")
                main_loop.create_task(restart_webrtc_client())
        if 'logging_level' in patch: 
            logging.root.setLevel(patch['logging_level'])
            logger.setLevel(patch['logging_level'])

    main_loop = asyncio.get_running_loop()
    module_client:IoTHubModuleClient = None
    webrtc_client:WebRTCClient = None
    webrtc_task = None
    try:        
        if not sys.version >= "3.5.3":
            logger.error(f'{datetime.datetime.now()}: This module requires python 3.5.3+. Current version of Python: {sys.version}.')
            raise Exception( 'This module requires python 3.5.3+. Current version of Python: %s' % sys.version )

        if settings.useAZIoT:
            logging.getLogger("azure.iot.device").setLevel(logging.WARNING)
            logger.info(f'{datetime.datetime.now()}: IoT Hub Client for Python')
            sampleRateInSeconds = 10        # can be updated through the module twin in IoTC

            # The client object is used to interact with your Azure IoT hub.
            module_client = IoTHubModuleClient.create_from_edge_environment()
            module_client.on_method_request_received = command_handler
            module_client.on_twin_desired_properties_patch_received = twin_update_handler
            await module_client.connect()
            await get_twin()

        if not build_gst_pipeline():
            logger.error(f'{datetime.datetime.now()}: Invalid camera source: {settings.cam_source}. Use test|rpi_cam|v4l2src')
            sys.exit(1)

        if(settings.stream_id is None):
            logger.error(f'{datetime.datetime.now()}: Missing stream id. Either set using the STREAM_ID envrionment variable, stream_id from IoTHub or the --streamid command line switch.')
            sys.exit(1)

        logger.info(f'{datetime.datetime.now()}: Booting up using settings: {settings}')
        webrtc_client = WebRTCClient(pipeline=settings.gst_pipeline, peer_id=settings.stream_id, server=settings.server)
        await webrtc_client.connect()

        # start send telemetry and receive commands        
        if settings.useAZIoT:
            webrtc_task = asyncio.create_task(webrtc_client.loop())
            await report_properties()
            await send_telemetry()
        else:
            await webrtc_client.loop()

    except asyncio.CancelledError:
        logger.info(f'{datetime.datetime.now()}: Main task was cancelled. Cleaning up.')
    except Exception as e:
        logger.error(f'{datetime.datetime.now()}: Unexpected error: {type(e)}: {e}')
        raise
    finally:
        if settings.useAZIoT and module_client is not None: await module_client.disconnect()

def check_plugins():
    needed = ["opus", "vpx", "nice", "webrtc", "dtls", "srtp", "rtp", "rtpmanager", "videotestsrc", "audiotestsrc"]
    missing = list(filter(lambda p: Gst.Registry.get().find_plugin(p) is None, needed))
    if len(missing):
        logger.error(f"{datetime.datetime.now()}: Missing gstreamer plugins: {missing}")
        return False
    return True

if __name__ == "__main__":
    logger.info(f'{datetime.datetime.now()}: Starting')
    Gst.init(None)
    if not check_plugins(): sys.exit(1)

    settings = SimpleNamespace(** {
        'stream_id': os.environ.get('STREAM_ID','htxi1234'),
        'server': os.environ.get('SERVER', 'wss://apibackup.obs.ninja:443'),
        'cam_source': os.environ.get('CAM_SOURCE', 'test'),
        'cam_source_params': os.environ.get('CAM_SOURCE_PARAMS', 'device=/dev/video0'),
        'custom_pipeline': os.environ.get('CUSTOM_PIPELINE', ''),
        'fps': int(os.environ.get('FPS', '15')),
        'width': int(os.environ.get('WIDTH', '1280')),
        'height': int(os.environ.get('HEIGHT', '720')),
        'caps': os.environ.get('CAPS', 'video/x-raw,width={width},height={height},framerate={fps}/1'),
        'useAZIoT': True if os.environ.get('USE_AZ_IOT', 'FALSE') == 'TRUE' else False,
        'gst_pipeline': ''        
    })

    parser = argparse.ArgumentParser()
    parser.add_argument('--streamid', help='Stream ID of the peer to connect to')
    parser.add_argument('--server', help='Handshake server to use, eg: "wss://backupapi.obs.ninja:443"')
    parser.add_argument('--cam_source', help='Video source type. Use test|rpi_cam|v4l2src.')
    parser.add_argument('--cam_source_params', help='Optional parameters for cam source. Currently only used for v4l2src to determine video device, i.e. device=/dev/video0')
    parser.add_argument('--custom_pipeline', help='Injection of custom gst pipeline plugins. Supplied plugins are injected between source and ! videoconvert ! to allow manipulation of the video source. If supplied, the value must terminate with a bang (!) Example: videoflip method=vertical-flip !')
    parser.add_argument('--width', help='video frame width. Must be supported by camera')
    parser.add_argument('--height', help='video frame height. Must be supported by camera')
    parser.add_argument('--framerate', help='video frame rate. Must be supported by camera')
    parser.add_argument('--caps', help='caps for gstreamer pipleine. Default is video/x-raw,width={width},height={height},framerate={fps}/1')
    parser.add_argument('--useAZIoT', help='Use Azure IoTEdge to manage from IoTHub. This requires that this program is deployed via an appropriate container. Connection to the Azure IoTHub is managed through the EdgeHub workload, so no connection parameters are required.', action='store_true')
    args = parser.parse_args()

    if(args.streamid is not None): settings.stream_id = args.streamid
    if(args.server is not None): settings.server = args.server
    if(args.cam_source is not None): settings.cam_source = args.cam_source
    if(args.cam_source_params is not None): settings.cam_source_params = args.cam_source_params
    if(args.custom_pipeline is not None): settings.custom_pipeline = args.custom_pipeline
    if(args.framerate is not None): settings.fps = int(args.framerate)
    if(args.width is not None): settings.width = int(args.width)
    if(args.height is not None): settings.height = int(args.height)
    if(args.useAZIoT): settings.useAZIoT = True

    try:
        asyncio.run(main(settings))
    except KeyboardInterrupt:
        logger.info(f'{datetime.datetime.now()}: Keyboard interrupt received.')
    finally:
        logger.info(f'{datetime.datetime.now()}: Exiting')
