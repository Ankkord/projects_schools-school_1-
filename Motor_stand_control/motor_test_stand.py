import struct
from collections import namedtuple

import serial
import threading
import json
import time
from serial_controller import SerialPortController
from id_motor_stand import *
from stand_options_manager import StandOptionManager
from safetyFlagsParser import SafetyFlagsParser

Pr = namedtuple("Pr", ["k", "b"])
Calibrations = namedtuple("Calibrations", ["v1", "i1", "f", "v2", "i2"])


class MotorTestPTPP:
    def __init__(self, port='COM3', baudrate=115200, parent=None):
        self.port = port
        self.baudrate = baudrate
        self.parent = parent
        self.serial_controller = SerialPortController(port, baudrate, on_error_callback=self._on_serial_error,
                                                      echo_plain_text=False)
        self.serial_controller.add_callback(self._receive_packet_callback)
        self.serial_error_callback = None
        self.options_manager = StandOptionManager()
        self.safety_flag_parser = SafetyFlagsParser()

        self.calibrations: dict[str, Pr] | None = dict()

        # read version
        self.serial_controller.send_data(PACKET_CONNECTION_MODULE, PACKET_CONNECTION_MODULE_GET_FIRMWARE_STR_NAME)

        # read calibrations
        self.serial_controller.send_data(StandID.GROUP, StandID.GET_CALIBRATIONS)
        self.serial_controller.send_data(StandID.GROUP, StandID.GET_OPTIONS)

        # Телеметрия
        self.telemetry = {
            "Voltage 1": 0.0,
            "Current 1": 0.0,
            "Thrust": 0,
            "Throttle": [0, 0]
        }

        # Флаги для управления потоками
        self.running = True

        self.started = False

        self.telemetry_callbacks = []

        # Запуск потоков
        self.send_thread = threading.Thread(target=self.send_commands)
        self.send_thread.start()
        self.thrust_zero_offset = 0

    def send_commands(self):
        while self.running:
            self.serial_controller.send_data(StandID.GROUP, StandID.KEEP_ALIVE)
            time.sleep(0.05)

    def decode_packet(self, group, command, length, data):
        if group == STAND_GROUP:
            if command == STAND_TELEMETRY:
                self._parce_telemetry(data)
            if command == STAND_GET_CALIBRATIONS_ANS:
                if length == 0:  # no settings
                    print("No calibrations on stand")  # fixme: add callback in ui
                else:
                    cals = struct.unpack("<10f", data)
                    self.calibrations["Voltage 1"] = Pr(cals[0], cals[1])
                    self.calibrations["Current 1"] = Pr(cals[2], cals[3])
                    self.calibrations["Thrust"] = Pr(cals[4], cals[5])
                    self.calibrations["Voltage 2"] = Pr(cals[6], cals[7])
                    self.calibrations["Current 2"] = Pr(cals[8], cals[9])
                    print(f"Calibration loaded from device: {self.calibrations}")

            if command == STAND_SET_CALIBRATIONS_ANS:
                print("New calibrations saved on stand (answer received)")
            if command == MODULE_STAND_SET_OPTIONS_ANS:
                print("Options saved on stand")
            if command == MODULE_STAND_GET_OPTIONS_ANS:
                if length == 0:
                    print("No options on stand")
                else:
                    self.options_manager.parse_settings(data)
        if group == PACKET_CONNECTION_MODULE:
            if command == PACKET_CONNECTION_MODULE_GET_FIRMWARE_STR_NAME_ANS:
                s = struct.unpack(f"{length}s", data)
                name, ver, = s[0].decode().strip().split("\r")
                print(name, ver)
                self.parent.check_version(name, ver)

    def _receive_packet_callback(self, packet):
        group = packet[0]
        command = packet[1]
        length = packet[2]
        data = packet[3:]
        self.decode_packet(group, command, length, data)

    def _parce_telemetry(self, data):
        v1, i1, v2, i2, f, _flags = struct.unpack('<5fI', data)
        flags = {  # hardware flags, for debug only
            "Door 1": bool(_flags & 1 << 0),
            "Door 2": bool(_flags & 1 << 1),
            "Halt": bool(_flags & 1 << 2),
        }
        self.safety_flag_parser.parse(_flags)
        if self.started and not self.safety_flag_parser.is_safe():
            print("Unsafe to spin! Stop all tests")
            self.parent._stop()  # todo: придумать более элегантный способ остановки теста

        self.telemetry.update({
            "Voltage 1": v1,
            "Voltage 2": v2,
            "Current 1": i1,
            "Current 2": i2,
            "Thrust": f,
            "Flags": self.safety_flag_parser.get_unsafe_names()
        })
        for callback in self.telemetry_callbacks:
            callback(self.telemetry.copy())

    def get_telemetry(self):
        """Получение текущей телеметрии."""
        return self.telemetry.copy()

    def stop(self):
        """Остановка потоков и закрытие порта."""
        self.running = False
        self.send_thread.join()
        self.serial_controller.close()

    def add_telemetry_callback(self, callback):
        """Добавление колбека для обработки телеметрии."""
        if callback not in self.telemetry_callbacks:
            self.telemetry_callbacks.append(callback)

    def remove_telemetry_callback(self, callback):
        """Удаление колбека для обработки телеметрии."""
        if callback in self.telemetry_callbacks:
            self.telemetry_callbacks.remove(callback)

    def _on_serial_error(self):
        print("Serial error!")
        if self.serial_error_callback:
            self.serial_error_callback()

    def stop_motor(self):
        self.started = False
        self.serial_controller.send_data(StandID.GROUP, StandID.DISABLE_SPIN)
        for i in range(len(self.telemetry["Throttle"])):
            self.telemetry["Throttle"][i] = 0

    def start(self):
        self.started = True
        self.serial_controller.send_data(StandID.GROUP, StandID.ENABLE_SPIN)

    def set_throttle(self, throttle):
        for i in range(len(self.telemetry["Throttle"])):
            self.set_throttle_multi(i, throttle)

    def set_throttle_multi(self, n, throttle):
        if n > len(self.telemetry["Throttle"]):
            raise IndexError(f"Incorrect motor index {n}")
        self.send_data(StandID.GROUP, StandID.SET_THROTTLE_CHANNEL, struct.pack("<BI", n, throttle))
        self.telemetry["Throttle"][n] = throttle

    def send_data(self, group_number: int, command_number: int, payload: bytes = b""):
        self.serial_controller.send_data(group_number, command_number, payload)

    """
    Применяет калибровки к пакету телеметрии и возвращает скорректированное значение
    """

    def apply_calibrations(self, telemetry: dict):
        if self.calibrations is None:
            return telemetry
        out = dict()
        for key, value in telemetry.items():
            if key not in self.calibrations.keys():
                out[key] = value
                continue
            out[key] = value * self.calibrations[key].k + self.calibrations[key].b
        return out

    def get_calibrated_telemetry(self):
        return self.apply_calibrations(self.get_telemetry())

    def set_calibrations(self, new_calibrations: dict[str, Pr]):
        self.calibrations.update(new_calibrations)
        print(f"New calibrations: {self.calibrations}")

    def get_calibrations(self) -> dict[str, Pr]:
        return self.calibrations

    """
    Сохраняет калибровки в постоянной памяти
    """

    def save_calibrations(self):
        v1_cal = self.calibrations.get("Voltage 1", None)
        c1_cal = self.calibrations.get("Current 1", None)
        t_cal = self.calibrations.get("Thrust", None)
        v2_cal = self.calibrations.get("Voltage 2", None)
        c2_cal = self.calibrations.get("Current 2", None)
        self.send_data(StandID.GROUP, StandID.SET_CALIBRATIONS, struct.pack(
            "<10f", *(v1_cal.k, v1_cal.b, c1_cal.k, c1_cal.b, t_cal.k, t_cal.b, v2_cal.k, v2_cal.b, c2_cal.k,
                      c2_cal.b)))  # плохо потому что нет никаких проверок на NaN, ну да ладно, проблема пользователя

    def save_options(self):
        self.send_data(StandID.GROUP, StandID.SET_OPTIONS, self.options_manager.pack_settings())

    def set_zero(self, telemetry):
        """Установка нуля для thrust."""
        self.thrust_zero_offset = (
                telemetry['Thrust'] * self.calibrations["Thrust"].k +
                self.calibrations["Thrust"].b
        )
        self.calibrations["Thrust"] = Pr(self.calibrations["Thrust"].k,
                                         self.calibrations["Thrust"].b - self.thrust_zero_offset)

    def send_service_cmd(self, n, cmd):
        self.send_data(StandID.GROUP, StandID.SERVICE_CMD, struct.pack("<2B", n, cmd))
