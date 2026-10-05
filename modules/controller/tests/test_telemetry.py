"""Offline tests for controller command completion and telemetry ownership.

Run with: python -m unittest discover -s modules/controller/tests
Only Azure and physical-camera boundaries are faked. The production app and
command modules execute unchanged. No network or hardware access is performed.
The tests use Python 3.7-compatible standard-library APIs.
"""
import asyncio
import importlib.util
import json
import logging
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

APP_DIR = Path(os.environ.get('CONTROLLER_APP_DIR', str(Path(__file__).resolve().parents[1] / 'app')))


class Camera:
    def __init__(self):
        self.position = (0.0, 0.0)
        self._turnedOff = True

    def pan_by(self, angle): self.position = (self.position[0] + angle, self.position[1])
    def pan_to(self, angle): self.position = (angle, self.position[1])
    def tilt_by(self, angle): self.position = (self.position[0], self.position[1] + angle)
    def tilt_to(self, angle): self.position = (self.position[0], angle)
    def turn_on(self): self._turnedOff = False
    def turn_off(self): self._turnedOff = True
    def test(self, *args): pass
    def reset(self): self.position = (0.0, 0.0)


class SleepGate:
    """Advance application timers explicitly instead of waiting for real time."""
    def __init__(self): self.waiters = []

    async def sleep(self, seconds):
        future = asyncio.get_event_loop().create_future()
        entry = (seconds, future)
        self.waiters.append(entry)
        try:
            await future
        finally:
            self.waiters.remove(entry)

    def release(self, seconds):
        released = 0
        for delay, future in list(self.waiters):
            if delay == seconds and not future.done():
                future.set_result(None)
                released += 1
        return released

    def count(self, seconds):
        return sum(delay == seconds and not future.done() for delay, future in self.waiters)


class Client:
    def __init__(self):
        self.messages = []
        self.responses = []
        self.properties = []
        self.failure = False
        self.telemetry_error = None
        self.command_error = None
        self.disconnected = False

    async def connect(self): pass
    async def disconnect(self): self.disconnected = True
    async def get_twin(self): return {'desired': {'period': 10}}

    async def send_message(self, message):
        if self.telemetry_error is not None:
            raise self.telemetry_error
        if self.failure:
            raise OSError('simulated telemetry failure')
        self.messages.append(json.loads(message))

    async def send_method_response(self, response):
        if self.command_error is not None:
            raise self.command_error
        self.responses.append(response)
    async def patch_twin_reported_properties(self, props): self.properties.append(props)


class Response:
    @staticmethod
    def create_from_method_request(request, status):
        return {'name': request.name, 'status': status}


def load_application(client, camera, gate):
    class Cam:
        @classmethod
        def get_names(cls): return ['camera']
        @classmethod
        def get(cls, name): return camera

    modules = {}
    for name in ['azure', 'azure.iot', 'azure.iot.device', 'azure.iot.device.aio', 'cam', 'controller', 'jsonmerge']:
        modules[name] = types.ModuleType(name)
    modules['azure.iot.device.aio'].IoTHubModuleClient = types.SimpleNamespace(create_from_edge_environment=lambda: client)
    modules['azure.iot.device'].MethodRequest = types.SimpleNamespace
    modules['azure.iot.device'].MethodResponse = Response
    modules['cam'].Cam = Cam
    modules['controller'].software_reset = lambda: None
    modules['jsonmerge'].merge = lambda original, update: dict(original, **update)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with patch.dict(sys.modules, modules):
        command = load('controller_command_telemetry_test', APP_DIR / 'command.py')
        with patch.dict(sys.modules, {'command': command}):
            app = load('controller_app_telemetry_test', APP_DIR / 'app.py')
    # Match the repository's Python 3.7 Docker target at the existing version
    # guard so these focused tests also run on newer development interpreters.
    app.sys = types.SimpleNamespace(version='3.7.17')
    app.asyncio = types.SimpleNamespace(gather=asyncio.gather, sleep=gate.sleep, CancelledError=asyncio.CancelledError)
    return app


async def settle():
    for _ in range(20):
        await asyncio.sleep(0)


class TelemetryTests(unittest.TestCase):
    def run_case(self, check):
        async def run():
            camera, client, gate = Camera(), Client(), SleepGate()
            app = load_application(client, camera, gate)
            tasks = [asyncio.create_task(app.main())]
            try:
                await settle()
                self.assertEqual(client.messages, [{'base': 0.0, 'elevation': 0.0}])
                self.assertEqual(gate.count(10), 1)

                def dispatch(name, payload=None):
                    task = asyncio.create_task(client.on_method_request_received(types.SimpleNamespace(name=name, payload=payload or {})))
                    tasks.append(task)
                    return task

                client.application = app
                await check(client, camera, gate, dispatch)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            self.assertTrue(client.disconnected)
            self.assertEqual(gate.waiters, [])
        asyncio.run(run())

    def check_command(self, name, payload, position):
        async def check(client, camera, gate, dispatch):
            task = dispatch(name, payload)
            await settle()
            self.assertTrue(task.done(), 'successful command callback must finish')
            self.assertIsNone(task.result())
            self.assertEqual(client.responses, [{'name': name, 'status': 202}])
            self.assertEqual(camera.position, position)
            self.assertEqual(client.messages[-1], {'base': position[0], 'elevation': position[1]})
            self.assertEqual(len(client.messages), 2)
            self.assertEqual(gate.count(10), 1)
            self.assertEqual(len(client.properties), 1 if name == 'Test' else 2)
        self.run_case(check)

    def test_pan_by_finishes(self): self.check_command('PanBy', {'angle': 5}, (5.0, 0.0))
    def test_pan_to_finishes(self): self.check_command('PanTo', {'angle': -7}, (-7, 0.0))
    def test_tilt_by_finishes(self): self.check_command('TiltBy', {'angle': 3}, (0.0, 3.0))
    def test_tilt_to_finishes(self): self.check_command('TiltTo', {'angle': 4}, (0.0, 4))
    def test_nudge_finishes(self): self.check_command('Nudge', {'direction': 'up'}, (0.0, 0.5))
    def test_camera_test_finishes(self): self.check_command('Test', {'countdown': 0}, (0.0, 0.0))

    def test_periodic_telemetry_continues(self):
        async def check(client, camera, gate, dispatch):
            for expected in range(2, 5):
                self.assertEqual(gate.release(10), 1)
                await settle()
                self.assertEqual(len(client.messages), expected)
                self.assertEqual(gate.count(10), 1)
        self.run_case(check)

    def test_repeated_commands_keep_one_periodic_loop(self):
        async def check(client, camera, gate, dispatch):
            tasks = [dispatch('PanBy', {'angle': 1}) for _ in range(4)]
            await settle()
            self.assertTrue(all(task.done() for task in tasks))
            self.assertEqual(camera.position, (4.0, 0.0))
            self.assertEqual(len(client.messages), 5)
            self.assertEqual(gate.release(10), 1)
            await settle()
            self.assertEqual(len(client.messages), 6)
            self.assertEqual(gate.count(10), 1)
        self.run_case(check)

    def test_telemetry_failure_does_not_hold_command(self):
        async def check(client, camera, gate, dispatch):
            client.failure = True
            task = dispatch('PanTo', {'angle': 5})
            await settle()
            self.assertTrue(task.done())
            self.assertIsNone(task.result())
            self.assertEqual(len(client.responses), 1)
            self.assertEqual(gate.count(10), 1)
            client.failure = False
            self.assertEqual(gate.release(10), 1)
            await settle()
            self.assertEqual(client.messages[-1], {'base': 5, 'elevation': 0.0})
        self.run_case(check)

    def test_periodic_failure_recovers(self):
        async def check(client, camera, gate, dispatch):
            client.failure = True
            self.assertEqual(gate.release(10), 1)
            await settle()
            self.assertEqual(len(client.messages), 1)
            self.assertEqual(gate.count(10), 1)
            client.failure = False
            self.assertEqual(gate.release(10), 1)
            await settle()
            self.assertEqual(len(client.messages), 2)
        self.run_case(check)

    def test_period_patch_changes_existing_loop_interval(self):
        async def check(client, camera, gate, dispatch):
            await client.on_twin_desired_properties_patch_received({'period': 20})
            self.assertEqual(gate.release(10), 1)
            await settle()
            self.assertEqual(gate.count(10), 0)
            self.assertEqual(gate.count(20), 1)
            self.assertEqual(gate.release(20), 1)
            await settle()
            self.assertEqual(len(client.messages), 3)
        self.run_case(check)

    def check_legacy_cancellation(self, boundary):
        # On Python 3.7 CancelledError is an Exception, unlike newer Pythons.
        # Model that inheritance to exercise both production cancellation guards.
        class LegacyCancelledError(Exception):
            pass

        async def check(client, camera, gate, dispatch):
            client.application.asyncio.CancelledError = LegacyCancelledError
            error = LegacyCancelledError('cancelled during ' + boundary)
            if boundary == 'telemetry':
                client.telemetry_error = error
            else:
                client.command_error = error
            task = dispatch('PanTo', {'angle': 5})
            await settle()
            self.assertTrue(task.done())
            with self.assertRaises(LegacyCancelledError) as raised:
                task.result()
            self.assertIs(raised.exception, error)
            self.assertEqual(gate.count(10), 1)
        self.run_case(check)

    def test_python37_cancellation_during_command_is_propagated(self):
        self.check_legacy_cancellation('command')

    def test_python37_cancellation_during_telemetry_is_propagated(self):
        self.check_legacy_cancellation('telemetry')

    def test_unknown_command_returns_without_extra_telemetry(self):
        async def check(client, camera, gate, dispatch):
            task = dispatch('Unknown')
            await settle()
            self.assertTrue(task.done())
            self.assertEqual(client.responses, [])
            self.assertEqual(len(client.messages), 1)
            self.assertEqual(gate.count(10), 1)
        self.run_case(check)


if __name__ == '__main__':
    unittest.main()
