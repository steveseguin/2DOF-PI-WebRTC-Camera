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
"""Module defining a meArm related json schemas"""
from controller import ServoSchema, ControllerSchema


cam_servo_schema = {
    "$id": "http://theRealThor.com/obscam.cam-servo.schema.json",
    "title": "2DOF Cam Servo Attributes",
    "description": "Describes additional cam servo attributes.",
    "definitions": {
        "cam_servo": {
            "type": "object",
            "properties": {
                "channel": {"type": "number"},
                "type": { "type": "string", "enum": ["custom", "SG-90", "ES08MAII"]},
                "attributes": {"ref": "http://theRealThor.com/obscam.servo-attributes.schema.json/#/definitions/servo_attributes"},
                "range": { "ref": "http://theRealThor.com/obscam.servo-attributes.schema.json/#/definitions/range"},
                "trim": {"type": "number"}
            },
            "required": [ "channel", "type", "range", "trim"]
        }
    },
    "allOf": [
        { "$ref": "#/definitions/cam_servo" }
    ]
}

cam_schema = {
    "$id": "http://theRealThor.com/obscam.cam.schema.json",
    "title": "2DOF Cam",
    "description": "Describes a cam controller setup.",
    "definitions": {
        "cam": {
            "type": "object",
            "properties": {
                "logging_level": {"type": "string", "enum": ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]},
                "angle-increment": {"type": "number"},
                "servos": {
                    "type": "object",
                    "properties": {
                        "base": { "$ref": "http://theRealThor.com/obscam.cam-servo.schema.json/#/definitions/cam_servo"},
                        "elevation": { "$ref": "http://theRealThor.com/obscam.cam-servo.schema.json/#/definitions/cam_servo"}
                    },
                    "required": ["base", "elevation"]
                },
            },
            "required": ["angle-increment", "servos"]
        },
        "cam-controller": {
            "type": "object",
            "properties": {
                "controller": { "$ref": "http://theRealThor.com/cam.servo-controller.schema.json/#/definitions/controller_attributes"},
                "cams": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/cam"},
                    "minItems": 1
                }
            },
            "required": ["controller", "cams"]
        },
        "environment": {
            "type": "array",
            "items": {"$ref": "#/definitions/cam-controller"},
            "minItems": 1,
            "maxItems": 255
        }
    },
    "oneOf": [
        { "$ref": "#/definitions/cam" },
        { "$ref": "#/definitions/cam-controller" },
        { "$ref": "#/definitions/environment" }
    ]
}

schema_store = {
    "http://theRealThor.com/obscom.servo-controller.schema.json": ControllerSchema,
    "http://theRealThor.com/obscam.servo-attributes.schema.json": ServoSchema,
    "http://theRealThor.com/obscam.cam-servo.schema.json": cam_servo_schema,
    "http://theRealThor.com/obscam.cam.schema.json": cam_schema
}
