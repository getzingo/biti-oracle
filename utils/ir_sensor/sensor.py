"""
Non-blocking IR Temperature Sensor Reader for Seeed Grove IR Sensor.

Reads serial data from an Arduino Nano in a background thread.
Thread-safe access to latest readings via get_readings().

Usage:
    from utils.ir_sensor import IRSensor
    sensor = IRSensor(port="/dev/ttyUSB0")
    sensor.start()
    readings = sensor.get_readings()
"""

import time
import threading
import asyncio
from typing import Optional, Dict

import serial

from utils.ir_sensor.calibration import (
    REFERENCE_VOL,
    OFFSET_VOL,
    calculate_ambient_temp,
    calculate_object_temp,
)


class IRSensor:
    """Non-blocking IR temperature sensor reader.

    Reads data from an Arduino Nano in a background thread.
    Thread-safe access to latest readings via get_readings().

    Calibration parameters as instance attributes:
        sensor.temp_calibration = 0.0   # ambient temp offset (°C)
        sensor.reference_vol = 0.500    # thermopile zero reference (V)
        sensor.offset_vol = 0.014       # thermopile calibration offset (V)
    """

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baud_rate: int = 9600,
        temp_calibration: float = 0.0,
        reference_vol: float = REFERENCE_VOL,
        offset_vol: float = OFFSET_VOL,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.temp_calibration = temp_calibration
        self.reference_vol = reference_vol
        self.offset_vol = offset_vol

        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # latest cached raw values
        self._raw_a6: int = 0
        self._raw_a7: int = 0
        self._timestamp: float = 0.0

    # ── lifecycle ──────────────────────────────────────────────

    def start(self) -> None:
        """Open serial port and start background reader thread."""
        if self._running:
            return
        self._serial = serial.Serial(self.port, self.baud_rate, timeout=1)
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background thread and close serial port."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        if self._serial and self._serial.is_open:
            self._serial.close()

    @property
    def is_running(self) -> bool:
        return self._running

    # ── serial reading ─────────────────────────────────────────

    def _read_loop(self) -> None:
        """Background loop: read lines from serial, update cache."""
        buf = ""
        while self._running and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting:
                    data = self._serial.read(self._serial.in_waiting).decode(
                        "utf-8", errors="ignore"
                    )
                    buf += data
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        self._process_line(line.strip())
                else:
                    time.sleep(0.02)
            except (serial.SerialException, OSError):
                time.sleep(0.5)

    def _process_line(self, line: str) -> None:
        """Parse 'IR:A6=123,A7=456' and update cache."""
        if not line.startswith("IR:"):
            return
        try:
            parts = line[3:].split(",")
            if len(parts) != 2:
                return
            a6 = int(parts[0].split("=")[1])
            a7 = int(parts[1].split("=")[1])
            with self._lock:
                self._raw_a6 = a6
                self._raw_a7 = a7
                self._timestamp = time.time()
        except (ValueError, IndexError):
            pass

    # ── public API ─────────────────────────────────────────────

    def get_readings(self) -> Dict:
        """Get latest sensor readings (non-blocking).

        Returns dict with: timestamp, raw_a6, raw_a7, object_c, ambient_c
        """
        with self._lock:
            raw_a6 = self._raw_a6
            raw_a7 = self._raw_a7
            ts = self._timestamp

        ambient_c = calculate_ambient_temp(raw_a7, self.temp_calibration)
        object_c = calculate_object_temp(
            raw_a6, ambient_c, self.reference_vol, self.offset_vol
        )

        return {
            "timestamp": ts,
            "raw_a6": raw_a6,
            "raw_a7": raw_a7,
            "object_c": round(object_c, 2),
            "ambient_c": round(ambient_c, 2),
        }

    async def get_readings_async(self) -> Dict:
        """Async wrapper — runs get_readings in a thread."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_readings)

    @property
    def raw_a6(self) -> int:
        with self._lock:
            return self._raw_a6

    @property
    def raw_a7(self) -> int:
        with self._lock:
            return self._raw_a7

    @property
    def object_temperature(self) -> float:
        return self.get_readings()["object_c"]

    @property
    def ambient_temperature(self) -> float:
        return self.get_readings()["ambient_c"]


if __name__ == "__main__":
    print("IR Sensor Test — Manufacturer Calibration")
    sensor = IRSensor()
    sensor.start()
    print("Waiting for data...\n")
    try:
        for i in range(15):
            time.sleep(1)
            r = sensor.get_readings()
            print(
                f"A6(OBJ)={r['raw_a6']:>4}  A7(SUR)={r['raw_a7']:>4}  "
                f"Amb={r['ambient_c']:>6.1f}°C  Obj={r['object_c']:>6.1f}°C"
            )
    except KeyboardInterrupt:
        pass
    finally:
        sensor.stop()
        print("Done.")
