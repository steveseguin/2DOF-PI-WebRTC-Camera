# Copyright (c) 2018 Avanade
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
# pylint: disable=C0103
"""Simple test routine for meArm on RPI"""
import time
import logging
import atexit
import json
from cam import Cam, CamServo
from controller import PCA9685, software_reset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
print('Press Ctrl-C to quit...')


# resolution = 4096
# frequency = 26500000 # This has been tweaked to provide exact pulse timing for the board. 
# servo_frequency = 50

# Initialise the PCA9685 using the default address (0x40).
# controller  = PCA9685(
#     0x40,
#     None,
#     frequency,
#     resolution,
#     servo_frequency)
#controller = PCA9685.from_json_file('pca9685.json')

cams = Cam.boot_from_json_file('cam.json')
all_cams = iter(cams.values())
for cam in all_cams:
    cam.test()
    time.sleep(0.5)

def shutdown():
    """shutdown
        Deletes the cams and then resets the controller
    """
    logger.info('Resetting servo and controller...')
    logger.info('Resetting registered cams [%s]' % ', '.join(map(str, Cam.get_names())))
    for name in Cam.get_names():
        cam = Cam.get(name)
        cam.reset()
        cam.turn_off()
    software_reset()

# restier shutdown steps
atexit.register(shutdown)
