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
import json
import datetime
import requests
import datetime

from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse
from azure.iot.device import MethodRequest
from cam import Cam

class CommandProcessor:

    @staticmethod
    def Commands(): 
        return {
            'Test': CommandProcessor.test
            #'Pan': CommandProcessor.pan,
            #'Tilt': CommandProcessor.tilt,
            #'Nudge': CommandProcessor.nudge
        }

    @staticmethod
    async def test(device_client:IoTHubModuleClient, request:MethodRequest):
        print(f'{datetime.datetime.now()}: Initiating test run')
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
                    'status': f'Device test completed at {datetime.datetime.now()}.'
                }
            }
        })
            
    