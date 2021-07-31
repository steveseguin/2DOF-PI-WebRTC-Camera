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

import psutil
import platform
import subprocess
import os
import cpuinfo
import requests
import datetime

token = "aa032a6ebc9f259cb4a32e0082714af2"

class Device():
    def __init__(self):
        self.__latitude = 0
        self.__longitude = 0
        self.__get_ip()
        self.__get_public_ip()
        self.__get_latlong()
        self.__get_device_properties()
        
    def __get_public_ip(self):
        #
        # get public facing ip address
        #
        response = requests.get("https://api.ipify.org/?format=json")
        if response.status_code != 200:
            raise EnvironmentError(f"Web request to api.ipify.org did not finish successfully. Response code: {response.status_code}")
        self.__public_ip = response.json()['ip']

    def __get_ip(self):
        #
        # get the internal IP address of the default route
        #
        c = "ip r | grep default | awk -F '[\/ ]+' '/default / {print $(NF-3)}'"
        ip = subprocess.check_output(c, shell=True).strip().decode('ascii')
        self.__ip = ip


    def __get_latlong(self):
        #
        # performs geo lookup using IP address 
        #
        parameters = {
            "access_key": token
        }
        response = requests.get(f"http://api.ipstack.com/{self.__public_ip}", params=parameters)
        if response.status_code != 200:
            raise EnvironmentError(f"Web request to api.ipstack.com did not finish successfully. Response code: {response.status_code}")
        self.__latitude = response.json()['latitude']
        self.__longitude = response.json()['longitude']

    def __get_device_properties(self):
        #
        # get CPU and other hardware properties
        #
        ci = cpuinfo.get_cpu_info()
        self.__cores = psutil.cpu_count()
        self.__max_frequency = int(psutil.cpu_freq().max)
        self.__hostname = platform.node()
        self.__arch = platform.machine()
        self.__cpu_info = ci['brand_raw']
        self.__cpu_features = ', '.join(ci['flags'])
        self.__os_version = ' '.join(platform.dist())
        self.__os_buildnumber = platform.platform()
        c = "cat /proc/cpuinfo"
        ai = subprocess.check_output(c, shell=True).strip().decode('ascii')
        for l in ai.split("\n"):
            if "Serial" in l: self.__board_serial = l.split(":")[1].strip()
            if "Model" in l: self.__board = l.split(":")[1].strip()

        self.__total_memory = round(psutil.virtual_memory().total/1000000000, 3)
        self.__total_disk = round(psutil.disk_usage('/').total/1000000000, 3)

    def __get_uptime_string(self):
        ups = datetime.datetime.fromtimestamp(psutil.boot_time())
        now = datetime.datetime.now()
        diff = now - ups
        periods = (
            (diff.days, "day", "days"),
            (int(diff.seconds / 3600) % 3600, "hour", "hours"),
            (int(diff.seconds / 60) % 60, "minute", "minutes"),
            (diff.seconds % 60, "second", "seconds"),
        ) 
        s = ""
        for period, singular, plural in periods:
            if period > 0:
                s += f" {period} {singular if period == 1 else plural}"
        return f"up{s}"

    @property
    def Info(self):
        #
        # Generates property json for update of hardware properties to IoT Central
        #
        payload = {
            'reportedLocation': {
                'value': {
                    'lat': self.__latitude,
                    'lon': self.__longitude
                }
            },
            'hostname': self.__hostname,
            'cpuArch': self.__arch,
            'cpuInfo': self.__cpu_info,
            'cpuCores': self.__cores,
            'cpuFeatures': self.__cpu_features,
            'cpuMaxfreq': self.__max_frequency,
            'baseboardModel': self.__board,
            'baseboardSerialNumber': self.__board_serial,
            'osVersion': self.__os_version,
            'osBuildNumber': self.__os_buildnumber,
            'ipLocal': self.__ip,
            'ipPublic': self.__public_ip,
            'memTotal': self.__total_memory,
            'diskTotal': self.__total_disk
        }
        return payload

    @property
    def Telemetry(self):
        #
        # Generates current telemetry
        #
        t = psutil.sensors_temperatures()
        m = psutil.virtual_memory()
        c = psutil.getloadavg()
        d = psutil.disk_usage('/')
        up = self.__get_uptime_string()
        payload = {
            'currentTemp': t['cpu_thermal'][0].current,
            'memFree': round(m.available/1000000000, 3),
            'memUsage': m.percent,
            'cpuLoading': c[0]*100/self.__cores,
            'cpuClock': int(psutil.cpu_freq().current),
            'diskFree': round(psutil.disk_usage('/').free/1000000000, 3),
            'diskUsage': round(psutil.disk_usage('/').percent, 3),
            'uptime': up
        }
        return payload