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
import logging
import datetime

from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse
from azure.iot.device import MethodRequest

class CommandProcessor:

    logger = logging.getLogger("htxi.module.device")

    @staticmethod
    def Commands(): 
        return {
            'PowerOffDevice': CommandProcessor.shutdown_device,
            'RebootDevice': CommandProcessor.reboot_device,
        }

    @staticmethod
    async def reboot_device(device_client:IoTHubModuleClient, request:MethodRequest):
        CommandProcessor.logger.info(f'{datetime.datetime.now()}: Rebooting host')
        countdown = request.payload.get("countdown",0)
        reason = request.payload.get("reason", "No reason provided")
        response = MethodResponse.create_from_method_request(
            request, status = 202
        )
        await device_client.send_method_response(response)             # immidiatly send acknowledgement of asynchronous command
        await asyncio.sleep(countdown)
        with open("/proc/sysrq-trigger", "a") as fo:                   # open sysrq-trigger file mounted into container via -v
            await device_client.patch_twin_reported_properties(        # send command status update via property update now sine we won't be able later
            {
                'RebootDevice': {
                    'value': {
                      'reason': reason,
                      'status': f'Device reboot intiated at {datetime.datetime.now()}.'
                    }
                }
            })
            fo.write("b")                                              # request the shutdown nothing after this matters

    @staticmethod
    async def shutdown_device(device_client:IoTHubModuleClient, request:MethodRequest):
        CommandProcessor.logger.info(f'{datetime.datetime.now()}: Shutting down host')
        countdown = request.payload.get("countdown",0)
        reason = request.payload.get("reason", "No reason provided")
        response = MethodResponse.create_from_method_request(
            request, status = 202
        )
        await device_client.send_method_response(response)             # immidiatly send acknowledgement of asynchronous command
        await asyncio.sleep(countdown)    
        with open("/proc/sysrq-trigger", "a") as fo:                   # open sysrq-trigger file mounted into container via -v
            await device_client.patch_twin_reported_properties(        # send command status update via property update now sine we won't be able later
            {
                'RebootDevice': {
                    'value': {
                      'reason': reason,
                      'status': f'Device reboot intiated at {datetime.datetime.now()}.'
                    }
                }
            })
            fo.write("o")                                              # request the shutdown nothing after this matters