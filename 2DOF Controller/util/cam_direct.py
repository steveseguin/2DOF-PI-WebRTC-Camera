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
# pylint: disable=C0103
"""Simple test program for servo actuation"""
import time
import logging
import atexit
from controller import PCA9685, Servo, ServoAttributes, CustomServoAttributes, MiuzeiSG90Attributes, ES08MAIIAttributes, software_reset

# Uncomment to enable debug output.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# frequency = 26500000 # This has been tweaked to provide exact pulse timing for the board. 
# resolution = 4096
# servo_frequency = 50

# Initialise the PCA9685 using the default address (0x40).
# pwm  = PCA9685(
#     0x40,
#     None,
#     frequency,
#     resolution,
#     servo_frequency)
pwm = PCA9685.from_json_file('pca9685.json')

# Alternatively specify a different address and/or bus:
# pwm = Adafruit_PCA9685.PCA9685(address=0x41, busnum=2)

# attributes = MiuzeiSG90Attributes()
attributes = CustomServoAttributes.from_json_file('servo.json')
base_channel = 15
elevation_channel = 14

pwm.set_off(14, False)
pwm.set_off(15, False)
pwm.add_servo(base_channel, attributes)
pwm.add_servo(elevation_channel, attributes)

def shutdown():
    """Resets the cam at neutral position and then resets the controller"""
    logger.info('Resetting cam and controller...')
    pwm.set_servo_angle(base_channel, base_neutral_angle)
    pwm.set_servo_angle(elevation_channel, elevation_neutral_angle)
    time.sleep(5)
    software_reset()
    pwm.set_off(14, False)
    pwm.set_off(15, False)

# restier shutdown steps
atexit.register(shutdown)

# arm neutrals and boundaries
elevation_neutral_angle = 68
elevation_max_angle = 85
elevation_min_angle = 25

base_neutral_angle = 0
base_max_angle = 85
base_min_angle = -85

# current angles
base_angle = base_neutral_angle
elevation_angle = elevation_neutral_angle

# movement increment in degrees
inc = 0.2

logger.info('Press Ctrl-C to quit...')
pwm.set_servo_angle(base_channel, base_angle) 
pwm.set_servo_angle(elevation_channel, elevation_neutral_angle) 

while True:
    while base_angle < base_max_angle:
        pwm.set_servo_angle(base_channel, base_angle)
        base_angle += inc
        if base_angle > base_max_angle: base_angle = base_max_angle

    while elevation_angle > elevation_min_angle:
        pwm.set_servo_angle(elevation_channel, elevation_angle)    
        elevation_angle -= inc
        if elevation_angle < elevation_min_angle: elevation_angle = elevation_min_angle
    
    time.sleep(2)

    while base_angle > base_min_angle:
        pwm.set_servo_angle(base_channel, base_angle)
        base_angle -= inc
        if base_angle < base_min_angle: base_angle = base_min_angle

    while elevation_angle < elevation_max_angle:
        pwm.set_servo_angle(elevation_channel, elevation_angle)
        elevation_angle += inc
        if elevation_angle > elevation_max_angle: elevation_angle = elevation_max_angle
        

    time.sleep(2)

    while base_angle < base_neutral_angle:
        pwm.set_servo_angle(base_channel, base_angle)
        base_angle += inc

    while elevation_angle > elevation_neutral_angle:
        pwm.set_servo_angle(elevation_channel, elevation_angle)
        elevation_angle -= inc

