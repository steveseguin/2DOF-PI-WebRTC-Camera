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
"""Module allowing control of a camera position using the RPI"""
import time
import logging
import json
from typing import Dict, List, Tuple
from jsonschema import validate, RefResolver, Draft4Validator, ValidationError, SchemaError
from controller import PCA9685, Servo, ServoAttributes, MiuzeiSG90Attributes, ES08MAIIAttributes, CustomServoAttributes, software_reset
from .cam_servo import CamServo
from .schemas import cam_schema, schema_store

class Cam(object):
    """Control camera position"""

    # arm neutrals and boundaries
    base_neutral_angle = 0.0         # servo angle for hip neutral position
    base_max_angle = 84.5            # servo angle for hip max position
    base_min_angle = -84.5           # servo angle for hip min position
    base_trim = 0.0

    elevation_neutral_angle = 40.0   # servo angle for shoulder neutral position
    elevation_max_angle = 65.0       # servo angle for shoulder max position
    elevation_min_angle = -15.0      # servo angle for shoulder min position
    elevation_trim = 5.0
    _inc = 0.5                      # servo movement increment in degrees
    _instances = {}
    _controllers: List[int] = []

    def __init__(self, 
            controller: PCA9685,
            base_channel: int = 15,
            elevation_channel: int = 12,
            initialize: bool = True,
            logging_level: str = 'ERROR'):
        """__init__
        Default initialization of arm. Avoid using this and instead create a meArm using the meArm.createWithParameters
        method, which ensures that a meArm is not registered twice.
        
        :param controller: The controller to which the arm is attached. 
        :type controller: PCA9685

        :param base_channel: The channel for the base rotation servo.
        :type base_channel: int

        :param elevation_channel: The channel for the elevation servo.
        :type elevation_channel: int

        :param initialize: True to immidiately run the servo initialization, false to adjuist values after construction.
        :type initialize: bool

        :param logging_level: The logging level to use for this arm. 
        :type logging_level: string
        """
        self._servo_tag: str = str(base_channel).zfill(2) + str(elevation_channel).zfill(2)
        self._id: str = str(controller.address).zfill(6) + self._servo_tag
        self._logger = logging.getLogger("%s.%s" % (__name__, self._id))
        self._logger.setLevel(logging_level)

        if base_channel < 0 or base_channel > 15 or \
           elevation_channel < 0 or elevation_channel > 15:
            msg = "Servo channel values must be between 0 and 15"
            self._logger.error(msg)
            raise ValueError(msg)            

        if controller is None:
            msg = "You must supply a valid controller object to create a cam position controller"
            self._logger.error(msg)
            raise Exception(msg)

        if self._id in Cam._instances:
            msg = "cam Instance already exists. Cannot create a new instance. Release the existing \
                instance by calling Cam.delete()"
            self._logger.error(msg)
            raise Exception(msg)
        
        self._controller = controller
        self._turnedOff = False

        self.__setup_defaults(base_channel, elevation_channel)

        if initialize: self.initialize()
        Cam._instances[self._id] = self
        if controller.address not in Cam._controllers: Cam._controllers.append(controller.address)
        self._logger.info("cam position controller with id %s created", self._id)
    
    def __setup_defaults(self, base_channel: int, elevation_channel: int):
        """__setup_defaults
        Setup defaults for the servos based on static defaults.
        
        :param base_channel: The channel for the base rotation servo.
        :type base_channel: int

        :param elevation_channel: The channel for the camera elevation servo.
        :type elevation_channel: int
        """
        # defaults for servos
        self._base_servo = CamServo(base_channel, MiuzeiSG90Attributes(), 
                                Cam.base_neutral_angle, Cam.base_min_angle, Cam.base_max_angle, Cam.base_trim)
        self._elevation_servo = CamServo(elevation_channel, MiuzeiSG90Attributes(), 
                                Cam.elevation_neutral_angle, Cam.elevation_min_angle, Cam.elevation_max_angle, Cam.elevation_trim)
        self._base_angle = self._base_servo.neutral + self._base_servo.trim
        self._elevation_angle = self._elevation_servo.neutral + self._elevation_servo.trim
    
    @classmethod
    def boot_from_json_file(cls, json_file:str) -> Dict[str,object]:
        """boot_from_json_file
        Generates a cam contoller environment from json file
        :param json_file: name of the file containing the json data. Must adhere to cam.CamSchema
        :type json_file: str
        """
        with open(json_file) as file:
            data = json.load(file)
            resolver = RefResolver('', cam_schema, schema_store)
            validator = Draft4Validator(cam_schema, [], resolver)
            validator.check_schema(cam_schema)
            #if not validator.is_valid(data):
            #    raise ValidationError('Could not validate meArm json. Check your json file', instance = 1)
        return cls.boot_from_dict(data)

    @classmethod
    def boot_from_json(cls, json_string:str) -> Dict[str,object]:
        """boot_from_json
        Generates a cam controller environment from json data
        :param json_string: String containing the json data. Must adhere to cam.CamSchema
        :type json_string: str
        """
        data = json.loads(json_string)
        resolver = RefResolver('', cam_schema, schema_store)
        validator = Draft4Validator(cam_schema, [], resolver)
        validator.check_schema(cam_schema)
        #if not validator.is_valid(data):
        #    raise ValidationError('Could not validate meArm json. Check your json file', instance = 1)
        return cls.boot_from_dict(data)

    @classmethod
    def boot_from_dict(cls, data:Dict[str,object]) -> Dict[str,object]:
        """boot_from_dict
        Generates a cam controller environment from dictionary
        :param data: The dictionary containing the servo data. Must adhere to cam.CamSchema
        :type data: dictionary
        """
        if type(data) is list: d = data
        else: d = [data]
        for c in d:
            level = "INFO"
            controller = PCA9685.from_dict(c['controller'])
            if 'logging_level' in c['servos']: level = c['servos']['logging_level']

            tag = str(c['servos']['base']['channel']).zfill(2) + str(c['servos']['elevation']['channel']).zfill(2)
            id = str(controller.address).zfill(6) + tag
            if id in Cam._instances: Cam._instances[id].delete(False)
            obj = cls(controller, c['servos']['base']['channel'], c['servos']['elevation']['channel'], False, level)
            obj._base_servo = CamServo.from_dict(c['servos']['base'])
            obj._elevation_servo = CamServo.from_dict(c['servos']['elevation']) 
            obj._inc = c['servos']['angle_increment']
            obj.initialize()
            cls._instances[id] = obj
        return cls._instances

    @classmethod
    def createWithServoParameters(cls, controller: PCA9685,
            base_channel: int, elevation_channel: int) -> object:
        """createWithServoParameters
        Creates a cam controller using parameters.

        :param controller: The controller to which the cam servos are attached. 
        :type controller: PCA9685
                
        :param base_channel: The channel for the base servo.
        :type base_channel: int

        :param elevation_channel: The channel for the elevation servo.
        :type elevation_channel: int

        :return: A cam controller instance.
        :rtype: Cam
        """

        servo_tag = str(base_channel).zfill(2) + str(elevation_channel).zfill(2)
        id = str(controller.address).zfill(6) + servo_tag

        if id in Cam._instances: 
            return Cam._instances[id]

        obj = cls(controller, base_channel, elevation_channel, False)

        #override defaults for servos
        obj.initialize()
        cls._instances[id] = obj
        return obj

    @classmethod
    def shutdown(cls, clear:bool = False):
        """shutdown
        Deletes all cam controllers currently registered and shutsdown environment
        :param clear:   True to remove all cam registrations. Will require complete re-initialization
                        of the infrastructure to operate the cams again. 
        :type clear:    bool
        """
        cam: cls = None
        for key  in Cam._instances:
            cam = Cam._instances[key]
            cam.reset()
            cam.turn_off()
            cam.delete(False)
        if clear: 
            cls._instances.clear()
            software_reset()

    @classmethod
    def get(cls, id: str) -> object:
        """get
        Gets the cam controller with specified id. 

        :param id: The cam id.
        :type id: str

        :return: cam instance
        :rtype: Cam
        """
        if id in Cam._instances:
            return Cam._instances[id]
        raise KeyError("No cams with id %s", id)

    @classmethod
    def get_names(cls) -> List[str]:
        """get_names
        Gets a list of registered cams.

        :return: A list of cam names (ids)
        :rtype: [str]
        """
        return list(cls._instances.keys())

    @classmethod
    def get_controllers(cls) -> List[int]:
        """get_controllers
        Gets a list of registered controller addresses

        :return: A list of cam controller addresses
        :rtype: [int]
        """
        return cls._controllers.copy()

    @property
    def controller(self) -> int:
        """Gets the controller address for the cam

        :return: The address of the controller
        :rtype: int
        """
        return self._controller.address

    @property
    def name(self) -> str:
        """Gets the name for the cam

        :return: The name of the cam
        :rtype: str
        """
        return self._id

    @property
    def position(self) -> Tuple[float, float]:
        """Gets the current position of the gripper

        :return: The current position
        :rtype: 2 dimensional tuple of base and elevation angles.
        """
        return (self._base_angle, self._elevation_angle)

    @property 
    def boundaries(self) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
        """Returns the pan and tile boundaries for the cam

        :return: The boundaries for pan and tile
        :rtype: 2 dimenasional tupel of 2 dimensional typles, each containing the lower and uppor boundaries, neutral and trim for pan and tile respectively
        """
        return (
            (self._base_servo.min, self._base_servo.max, self._base_servo.neutral, self._base_servo.trim),
            (self._elevation_servo.min, self._elevation_servo.max, self._elevation_servo.neutral, self._elevation_servo.trim))

    def delete(self, reset:bool=True):
        """delete
        Deletes the meArm
        """
        self.turn_off()
        if reset: self.reset()
        del Cam._instances[self._id]

    def pan_to(self, angle: float) -> float:
        """ Pan the camera horizontally to the given angle. 
        
        :param angle: The angle to which to pan from the current position. Can be positive or negative.
        :type angle: float

        :return: The pan angle after the movement. Should be very close to angle.
        :rtype: float       
        """
        self.turn_on()
        if angle - self._base_servo.trim > self._base_servo.max: angle = self._base_servo.max + self._base_servo.trim 
        elif angle - self._base_servo.trim < self._base_servo.min: angle = self._base_servo.min + self._base_servo.trim 
        if self._base_angle - self._base_servo.trim > angle:
            while self._base_angle - self._base_servo.trim > angle:
                self._base_angle -= self._inc
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
        elif self._base_angle - self._base_servo.trim < angle: 
            while self._base_angle - self._base_servo.trim < angle:
                self._base_angle += self._inc
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
        self.turn_off()
        return self._base_angle

    def pan_by(self, angle: float) -> float:
        """ Pan the camera horizontally and incrementally by the given angle. 
        
        :param angle: The angle by which to increment the pan. Can be positive or negative.
        :type angle: float

        :return: The pan angle after the movement
        :rtype: float       
        """
        self.turn_on()
        a = self._base_angle + angle
        if a - self._base_servo.trim > self._base_servo.max: a = self._base_servo.max + self._base_servo.trim 
        elif a - self._base_servo.trim < self._base_servo.min: a = self._base_servo.min + self._base_servo.trim 
        if self._base_angle - self._base_servo.trim > a:
            while self._base_angle - self._base_servo.trim > a:
                self._base_angle -= self._inc
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
        elif self._base_angle - self._base_servo.trim < a: 
            while self._base_angle - self._base_servo.trim < a:
                self._base_angle += self._inc
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
        self.turn_off()
        return self._base_angle

    def tilt_to(self, angle: float) -> float:
        """ Tile the camera vertically to the given angle. 
        
        :param angle: The angle to which to tilt from the current elevation. Can be positive or negative.
        :type angle: float

        :return: The tilt angle after the movement. Should be very close to angle.
        :rtype: float       
        """
        self.turn_on()
        if angle - self._elevation_servo.trim > self._elevation_servo.max: angle = self._elevation_servo.max + self._elevation_servo.trim 
        elif angle - self._elevation_servo.trim < self._elevation_servo.min: angle = self._elevation_servo.min + self._elevation_servo.trim 
        if self._elevation_angle - self._elevation_servo.trim > angle:
            while self._elevation_angle - self._elevation_servo.trim > angle:
                self._elevation_angle -= self._inc
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)
        elif self._elevation_angle - self._elevation_servo.trim < angle: 
            while self._elevation_angle - self._elevation_servo.trim < angle:
                self._elevation_angle += self._inc
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)
        self.turn_off()
        return self._elevation_angle

    def tilt_by(self, angle: float) -> float:
        """ Tilt the camera incrementally by the given angle. 
        
        :param angle: The angle by which to increment the tilt. Can be positive or negative.
        :type angle: float

        :return: The tilt angle after the movement
        :rtype: float       
        """
        self.turn_on()
        a = self._elevation_angle + angle
        if a - self._elevation_servo.trim > self._elevation_servo.max: a = self._elevation_servo.max + self._elevation_servo.trim 
        elif a - self._elevation_servo.trim < self._elevation_servo.min: a = self._elevation_servo.min + self._elevation_servo.trim 
        if self._elevation_angle - self._elevation_servo.trim > a:
            while self._elevation_angle - self._elevation_servo.trim > a:
                self._elevation_angle -= self._inc
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)
        elif self._elevation_angle - self._elevation_servo.trim < a: 
            while self._elevation_angle - self._elevation_servo.trim < a:
                self._elevation_angle += self._inc
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)
        self.turn_off()
        return self._elevation_angle

    def initialize(self):
        """Registers the servo.""" 
        self._controller.add_servo(self._base_servo.channel, self._base_servo.attributes, False)
        self._controller.add_servo(self._elevation_servo.channel, self._elevation_servo.attributes, False)
        self.reset()
        self.turn_off()
        self._logger.info("cam with id %s initialized,", self._id)

    def reset(self):
        """reset
        Resets the cam at neutral position"""
        self._logger.info('Resetting cam %s...', self._id)
        
        # move to neutral angles      
        if self._base_angle - self._base_servo.trim > self._base_servo.neutral:
            while self._base_angle - self._base_servo.trim > self._base_servo.neutral:
                self._base_angle -= self._inc
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
        elif self._base_angle - self._base_servo.trim < self._base_servo.neutral: 
            while self._base_angle - self._base_servo.trim < self._base_servo.neutral:
                self._base_angle += self._inc
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)

        if self._elevation_angle - self._elevation_servo.trim > self._elevation_servo.neutral:
            while self._elevation_angle - self._elevation_servo.trim > self._elevation_servo.neutral:
                self._elevation_angle -= self._inc
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)        
        if self._elevation_angle - self._elevation_servo.trim < self._elevation_servo.neutral:
            while self._elevation_angle - self._elevation_servo.trim < self._elevation_servo.neutral:
                self._elevation_angle += self._inc
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)        
       
        self._base_angle = self._base_servo.neutral + self._base_servo.trim
        self._elevation_angle = self._elevation_servo.neutral + self._elevation_servo.trim
        self._controller.set_servo_angle(self._base_servo.channel, self._base_angle)
        self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle)     
        self._logger.info("arm reset to (%f, %f)", self._base_servo.neutral, self._elevation_servo.neutral)
        time.sleep(0.3)

    def turn_off(self):
        """turn_off
        Turns all servos of the cam to full off
        """
        if not self._turnedOff:
            self._controller.set_off(self._base_servo.channel, True)
            self._controller.set_off(self._elevation_servo.channel, True)
            self._turnedOff = True
            self._logger.warning(f'Servo channels for {self._id} have been turned off.')

    def turn_on(self):
        """turn_on
        Turns all servos of the cam to pwm
        """
        if self._turnedOff:
            self._controller.set_off(self._base_servo.channel, False)
            self._controller.set_off(self._elevation_servo.channel, False)
            self._turnedOff = False
            self._logger.warning(f'Servo channels for {self._id} have been turned on.')

    def test(self, repeat: bool = False) -> int:
        """Simple loop to test the cam controller
        
        :param repeat: If True repeat the test routine until interupted.
        :type repeat: bool

        :return: Number of operations executed
        :rtype: int
        """
        if repeat: self._logger.info('Press Ctrl-C to quit...')
        self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
        self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)

        ops = 0
        while True:     
            while self._base_angle - self._base_servo.trim < self._base_servo.max:
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
                self._base_angle += self._inc
                if self._base_angle - self._base_servo.trim > self._base_servo.max: self._base_angle = self._base_servo.max + self._base_servo.trim
                ops += 1

            while self._elevation_angle - self._elevation_servo.trim > self._elevation_servo.min:
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)
                self._elevation_angle -= self._inc
                if self._elevation_angle - self._elevation_servo.trim < self._elevation_servo.min: self._elevation_angle = self._elevation_servo.min + self._elevation_servo.trim
                ops += 1

            while self._base_angle - self._base_servo.trim > self._base_servo.min:
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
                self._base_angle -= self._inc
                if self._base_angle - self._base_servo.trim < self._base_servo.min: self._base_angle = self._base_servo.min + self._base_servo.trim
                ops += 1

            while self._elevation_angle - self._elevation_servo.trim < self._elevation_servo.max:
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)
                self._elevation_angle += self._inc
                if self._elevation_angle - self._elevation_servo.trim > self._elevation_servo.max: self._elevation_angle = self._elevation_servo.max + self._elevation_servo.trim
                ops += 1
            
            while self._base_angle - self._base_servo.trim < self._base_servo.neutral:
                self._controller.set_servo_angle(self._base_servo.channel, self._base_angle - self._base_servo.trim)
                self._base_angle += self._inc
                ops += 1

            while self._elevation_angle - self._elevation_servo.trim > self._elevation_servo.neutral:
                self._controller.set_servo_angle(self._elevation_servo.channel, self._elevation_angle - self._elevation_servo.trim)
                self._elevation_angle -= self._inc
                ops += 1

            if not repeat: break
        
        return ops
