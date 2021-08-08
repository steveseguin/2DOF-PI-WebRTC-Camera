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
import asyncio
import datetime
import datetime

from typing import List
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse
from azure.iot.device import MethodRequest
from cam import Cam

class CommandProcessor:

    @staticmethod
    def Commands(): 
        return {
            'Test': CommandProcessor.test,
            'PanBy': CommandProcessor.pan_or_tilt,
            'PanTo': CommandProcessor.pan_or_tilt,
            'TiltBy': CommandProcessor.pan_or_tilt,
            'TiltTo': CommandProcessor.pan_or_tilt,
            'Nudge': CommandProcessor.nudge
        }

    @staticmethod
    async def test(device_client:IoTHubModuleClient, request:MethodRequest):
        print(f'{datetime.datetime.now()}: [INFO] Initiating test run')
        countdown = request.payload.get("countdown", 0)
        response = MethodResponse.create_from_method_request(
            request, status = 202
        )
        await device_client.send_method_response(response)         # immidiatly send acknowledgement of asynchronous command
        await asyncio.sleep(countdown)

        names:List[str] = Cam.get_names()
        cam:Cam = Cam.get(names[0])
        cam.test(False)
        await device_client.patch_twin_reported_properties(        # send command status update via property update
        {
            'Test': {
                'value': {
                    'status': f'Device test completed at {datetime.datetime.now()}.',
                    'position': {
                        'base': cam.position[0],
                        'elevation': cam.position[1]
                    }
                }
            }
        })

    @staticmethod
    async def pan_or_tilt(device_client:IoTHubModuleClient, request:MethodRequest):
        print(f'{datetime.datetime.now()}: Initiating {request.name}')
        angle = request.payload.get("angle", 0)
        response = MethodResponse.create_from_method_request(
            request, status = 202
        )
        await device_client.send_method_response(response)         # immidiatly send acknowledgement of asynchronous command
        names:List[str] = Cam.get_names()
        cam:Cam = Cam.get(names[0])
        if request.name == 'PanBy': 
            cam.pan_by(angle)
            props = {'PanBy': {}}
        elif request.name == 'PanTo': 
            cam.pan_to(angle)
            props = {'PanTo': {}}
        elif request.name == 'TiltBy': 
            cam.tilt_by(angle)
            props = {'TiltBy': {}}
        elif request.name == 'TiltTo': 
            cam.tilt_to(angle)
            props = {'TiltTo': {}}
        else:
            print(f'{datetime.datetime.now()}: [ERROR] Unknown method: {request.name}')
            return
        
        # send command status update via property update
        props[request.name] = {
                'value': {
                    'status': f'Command {request.name} completed at {datetime.datetime.now()}.',
                    'position': {
                        'base': cam.position[0],
                        'elevation': cam.position[1]
                    }
                }
            }
        await device_client.patch_twin_reported_properties(props)
        await device_client.patch_twin_reported_properties({
            'position': {
                'base': cam.position[0],
                'elevation': cam.position[1]
            }
        })

    @staticmethod 
    async def nudge(device_client:IoTHubModuleClient, request:MethodRequest):
        print(f'{datetime.datetime.now()}: Initiating {request.name}')
        direction = request.payload.get("direction", "")
        response = MethodResponse.create_from_method_request(
            request, status = 202
        )
        await device_client.send_method_response(response)         # immidiatly send acknowledgement of asynchronous command
        names:List[str] = Cam.get_names()
        cam:Cam = Cam.get(names[0])
        pos = [cam.position[0], cam.position[1]]
        pos_prime = [cam.position[0], cam.position[1]]
        if direction == 'up': 
            pos_prime[1] -= 5
            pos[1] += 0.5
        elif direction == 'down':
            pos_prime[1] += 5
            pos[1] -= 0.5               
        elif direction == 'right':
            pos_prime[0] += 5
            pos[0] -= 0.5
        elif direction == 'left':
            pos_prime[0] -= 5
            pos[0] += 0.5
        cam.turn_on()
        cam.position = (pos_prime[0], pos_prime[1])
        cam.position = (pos[0], pos[1])
        cam.turn_off()
        
        # send command status update via property update
        props = {
            'Nudge': {
                'value': {
                    'status': f'Command {request.name} completed at {datetime.datetime.now()}.',
                    'position': {
                        'base': cam.position[0],
                        'elevation': cam.position[1]
                    }
                }
            }
        }
        await device_client.patch_twin_reported_properties(props)
        await device_client.patch_twin_reported_properties({
            'position': {
                'base': cam.position[0],
                'elevation': cam.position[1]
            }
        })