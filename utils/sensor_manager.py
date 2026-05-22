"""
Sensor Manager for The Oracle of Selphi.

Wraps hardware sensors and provides normalised readings for the Oracle app.

Sensors:
  - HC-SR04 Ultrasonic (Pi GPIO 16/12): hand proximity detection
  - Grove IR Temperature via Arduino Nano (/dev/ttyUSB0): mood from body temp

When BOARD=raspi is set, real sensors are used.
Otherwise simulated random values for development/testing.
"""

import os
import random
import time
from typing import Optional


class SensorManager:
    """Manages all sensors and provides a unified interface for the Oracle app.

    Ultrasonic sensor detects hand presence (proximity).
    IR temperature sensor reads body heat to determine fortune mood (0-100).

    Mood mapping (in Fortune._derive_mood_from_sensor):
        0-20   → gentle
        21-40  → dramatic
        41-60  → cynical
        61-80  → chaotic
        81-100 → obliterating
    """

    # HC-SR04 pins (BCM numbering)
    TRIG_PIN = 16
    ECHO_PIN = 12

    # Hand detection: distance drops below this fraction of baseline
    # (e.g. baseline=100cm, hand at 30cm → 0.3; baseline=2cm, hand at 1cm → 0.5)
    HAND_DISTANCE_RATIO: float = 0.7
    # Minimum absolute drop in cm to avoid noise triggering
    MIN_HAND_DROP_CM: float = 0.5

    # Debounce: number of consecutive hand-present readings before triggering
    HAND_DEBOUNCE_FRAMES: int = 5

    # IR: max object-ambient differential for mapping to 0-100
    # Realistic hand diff ~1-2°C with this sensor at close range
    MAX_DIFF_CELSIUS: float = 2.0

    def __init__(self):
        self._use_real = os.getenv("BOARD") == "raspi"
        self._ir_sensor = None
        self._gpio = None
        self._started = False
        self._last_random = 50
        self._last_distance: Optional[float] = None
        self._baseline_distance: Optional[float] = None
        self._hand_frames: int = 0
        self._cooldown_until: float = 0.0

    def start(self) -> None:
        """Initialise and start all sensors."""
        if self._started:
            return
        self._started = True

        if self._use_real:
            self._init_ultrasonic()
            self._init_ir_sensor()
        else:
            print("[SENSOR] Running in simulation mode (no BOARD=raspi)")

    def stop(self) -> None:
        """Stop all sensors and release resources."""
        if self._ir_sensor:
            self._ir_sensor.stop()
            print("[SENSOR] IR sensor stopped")
        if self._gpio:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
            self._gpio = None
        self._started = False

    # ── ultrasonic (hand detection) ────────────────────────────

    def _init_ultrasonic(self) -> None:
        """Set up HC-SR04 ultrasonic sensor on GPIO."""
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.TRIG_PIN, GPIO.OUT)
            GPIO.setup(self.ECHO_PIN, GPIO.IN)
            GPIO.output(self.TRIG_PIN, GPIO.LOW)
            time.sleep(0.5)
            # Establish baseline distance during init
            self._baseline_distance = self._read_distance_raw()
            self._last_distance = self._baseline_distance
            print(f"[SENSOR] Ultrasonic ready (baseline={self._baseline_distance:.1f}cm)")
        except Exception as e:
            print(f"[SENSOR] Ultrasonic not available: {e}")
            self._gpio = None

    def _read_distance_raw(self) -> float:
        """Read raw distance from HC-SR04 in cm. Returns large value on timeout."""
        if not self._gpio:
            return 999.0
        GPIO = self._gpio
        # 10µs trigger pulse
        GPIO.output(self.TRIG_PIN, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(self.TRIG_PIN, GPIO.LOW)

        timeout = time.time() + 0.1
        pulse_start = time.time()
        while GPIO.input(self.ECHO_PIN) == 0 and time.time() < timeout:
            pulse_start = time.time()

        pulse_end = time.time()
        while GPIO.input(self.ECHO_PIN) == 1 and time.time() < timeout:
            pulse_end = time.time()

        duration = pulse_end - pulse_start
        return duration * 17150  # speed of sound / 2

    def get_distance(self) -> float:
        """Get current distance in cm (reads sensor)."""
        if self._use_real and self._gpio:
            try:
                d = self._read_distance_raw()
                self._last_distance = d
                return d
            except Exception:
                return self._last_distance or 999.0
        # Simulated: random distance for testing
        self._last_distance = random.uniform(10, 100)
        return self._last_distance

    def is_hand_present(self) -> bool:
        """Check if a hand is detected near the sensor.

        Uses ultrasonic: if distance drops significantly below baseline
        for several consecutive readings, something (a hand) is close.

        Includes debounce (HAND_DEBOUNCE_FRAMES) and a cooldown window
        after returning True to prevent immediate re-triggering.
        """
        # Honour cooldown
        if time.monotonic() < self._cooldown_until:
            return False

        detected = self._hand_detected_raw()
        if detected:
            self._hand_frames += 1
        else:
            self._hand_frames = 0
            return False

        if self._hand_frames >= self.HAND_DEBOUNCE_FRAMES:
            self._hand_frames = 0
            self._cooldown_until = time.monotonic() + 5.0  # 5-second cooldown
            return True
        return False

    def _hand_detected_raw(self) -> bool:
        """Single-frame hand detection (no debounce)."""
        d = self.get_distance()
        if self._baseline_distance is None:
            self._baseline_distance = d
            return False
        if self._baseline_distance <= 0:
            return False
        drop = self._baseline_distance - d
        ratio = d / self._baseline_distance if self._baseline_distance > 0 else 1.0
        return ratio < self.HAND_DISTANCE_RATIO and drop >= self.MIN_HAND_DROP_CM

    # ── IR temperature (mood) ──────────────────────────────────

    def _init_ir_sensor(self) -> None:
        """Set up IR temperature sensor via Arduino."""
        try:
            from utils.ir_sensor import IRSensor
            self._ir_sensor = IRSensor(
                port="/dev/ttyUSB0",
                temp_calibration=-2.6,
            )
            self._ir_sensor.start()
            print(f"[SENSOR] IR sensor started on {self._ir_sensor.port}")
        except Exception as e:
            print(f"[SENSOR] IR sensor not available: {e}")

    def read(self) -> int:
        """Return a normalised sensor value 0-100 for fortune mood.

        With real sensor: maps object-ambient temperature differential.
        Without: random walk for development/testing.
        """
        if self._use_real and self._ir_sensor:
            return self._read_ir_mood()
        return self._read_simulated()

    def _read_ir_mood(self) -> int:
        """Read IR sensor and map differential to 0-100."""
        try:
            r = self._ir_sensor.get_readings()
            diff = r["object_c"] - r["ambient_c"]
            clamped = max(0.0, min(self.MAX_DIFF_CELSIUS, diff))
            return int((clamped / self.MAX_DIFF_CELSIUS) * 100)
        except Exception as e:
            print(f"[SENSOR] IR read error: {e}")
            return 0

    def _read_simulated(self) -> int:
        """Simulated random-walk sensor reading."""
        delta = random.randint(-15, 15)
        self._last_random = max(0, min(100, self._last_random + delta))
        return self._last_random

    def read_detailed(self) -> dict:
        """Return full sensor details for debugging."""
        result = {
            "sensor_val": self.read(),
            "mode": "simulated",
            "distance_cm": self.get_distance(),
            "hand_present": self.is_hand_present(),
        }
        if self._use_real and self._ir_sensor:
            try:
                r = self._ir_sensor.get_readings()
                result.update({
                    "mode": "ir_sensor",
                    "object_c": r["object_c"],
                    "ambient_c": r["ambient_c"],
                    "raw_a6": r["raw_a6"],
                    "raw_a7": r["raw_a7"],
                })
            except Exception:
                pass
        return result

    @property
    def is_real(self) -> bool:
        return self._use_real and self._ir_sensor is not None