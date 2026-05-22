#!/usr/bin/env python3
"""
Text-mode simulator for The Oracle of Selphi
Simulates the state machine, sensor inputs (random 0-100), and fortune generation.
Uses Fortune class with fallback to fortune.db.
"""
import time
import random
import os

from utils.classes.Fortune import Fortune
from utils.config import config
from utils.sensor_manager import SensorManager

SENSING_MIN_DURATION = config.sensing_min_duration_seconds * 1000
SENSING_MAX_DURATION = config.sensing_max_duration_seconds * 1000


class OracleSimulator:
    STATE_IDLE = "idle"
    STATE_SENSING = "sensing"
    STATE_GENERATING = "generating"
    STATE_FORTUNE = "fortune"
    STATE_FAILED = "failed"

    def __init__(self):
        self.state = self.STATE_IDLE
        self.sensing_start_time = 0.0
        self.sensing_duration = 0.0  # set when sensing starts
        self.fortune: Fortune = None
        self.fortune_text = ""
        self.fortune_source = ""
        self.last_sensor_value = 0
        self.start_sensing_time = 3.0
        self.sensor = SensorManager()
        self.sensor.start()

    def generate_sensor_value(self) -> int:
        """Read sensor value (real IR on Pi, simulated random walk otherwise)."""
        return self.sensor.read()

    def start_sensing(self):
        self.state = self.STATE_SENSING
        self.sensing_start_time = time.time() * 1000  # convert to ms for consistency
        # Choose random duration between min and max
        self.sensing_duration = random.randint(SENSING_MIN_DURATION, SENSING_MAX_DURATION)
        self.fortune = None
        self.fortune_text = ""
        self.fortune_source = ""
        print(f"\n[SENSING START] Duration: {self.sensing_duration/1000:.1f}s")

    def sensing_loop(self):
        """Run one step of sensing; returns True if still sensing, False if finished."""
        elapsed = time.time() * 1000 - self.sensing_start_time
        if elapsed >= SENSING_MAX_DURATION:
            print(f"[SENSING] Max duration reached ({SENSING_MAX_DURATION}ms).")
            # Don't fail yet - let fortune generation attempt
            self.state = self.STATE_GENERATING
            return False
        if elapsed >= self.sensing_duration:
            print(f"[SENSING] Complete after {elapsed:.0f}ms.")
            self.state = self.STATE_GENERATING
            return False
        # Generate sensor value
        sensor_val = self.generate_sensor_value()
        # Select message index based on elapsed time (like in main.py)
        msg_index = int(elapsed // 2500) % len(config.sensing_messages)
        message = config.sensing_messages[msg_index]
        print(f"[SENSING] {elapsed:6.0f}ms | Sensor: {sensor_val:3d} | {message}")
        # Start fortune generation early during sensing
        if elapsed >= self.start_sensing_time * 1000 and self.fortune is None:
            self._start_fortune_generation(sensor_val)

        return True

    def _start_fortune_generation(self, sensor_val: int):
        """Start Fortune generation in background thread."""
        print(f"[GENERATING] Starting fortune generation with sensor={sensor_val}...")
        self.fortune = Fortune(sensor_val=sensor_val)
        self.fortune.start_generation()

    def generate_fortune(self):
        """Wait for fortune generation to complete."""
        if self.fortune is None:
            # Should not happen, but handle gracefully
            sensor_val = self.last_sensor_value
            self._start_fortune_generation(sensor_val)

        if self.fortune.fortune_ready:
            if self.fortune.result:
                self.fortune_text = self.fortune.result
                self.fortune_source = self.fortune.source
                self.state = self.STATE_FORTUNE
                print(f"[GENERATING] Fortune ready (source: {self.fortune_source})")
            else:
                # API failed and no fallback available
                self.state = self.STATE_FAILED
                print("[GENERATING] Fortune generation failed - no result")
        else:
            # Still waiting
            print("[GENERATING] Waiting for oracle...")

    def show_fortune(self):
        source_label = "[API]" if self.fortune_source == "api" else "[FALLBACK DB]"
        print(f"\n{'='*60}")
        print("           THE ORACLE SPEAKS")
        print(f"           {source_label}")
        print(f"{'='*60}")
        print(f"\n    {self.fortune_text}\n")
        print(f"{'='*60}")
        self.state = self.STATE_IDLE
        self.last_sensor_value = 0  # reset

    def show_failed(self):
        print(f"\n{'='*60}")
        print("           THE ORACLE IS SILENT")
        print(f"{'='*60}")
        print("\n    The connection to the oracle has failed.")
        print("    No fortunes available in the database.")
        print("    Please try again later.\n")
        print(f"{'='*60}")
        self.state = self.STATE_IDLE
        self.last_sensor_value = 0

    def run(self):
        print("\n" + "="*60)
        print("    DAS ORAKEL VON SELPHI - Text Simulator")
        print("    With fallback to fortune.db")
        print("="*60)
        print("\nPress ENTER to simulate hand reading...")
        print("(Type 'quit' to exit)\n")

        try:
            while True:
                if self.state == self.STATE_IDLE:
                    # Auto-trigger if hand detected (simulated or real)
                    if self.sensor.is_hand_present():
                        print("\n[HAND DETECTED]")
                        self.start_sensing()
                        continue
                    cmd = input(">>> ").strip().lower()
                    if cmd == "quit":
                        print("\nThe oracle fades into darkness... Goodbye.")
                        break
                    if cmd == "" or cmd == "hand":
                        self.start_sensing()
                    else:
                        print("Press ENTER to begin sensing, or type 'quit' to exit.")

                elif self.state == self.STATE_SENSING:
                    # Simulate sensing for a few steps then decide
                    time.sleep(0.5)  # simulate time passing
                    still_sensing = self.sensing_loop()
                    if not still_sensing:
                        # state has changed to generating
                        pass

                elif self.state == self.STATE_GENERATING:
                    time.sleep(0.5)  # poll every 500ms
                    self.generate_fortune()

                elif self.state == self.STATE_FORTUNE:
                    self.show_fortune()
                    print("\nPress ENTER to consult again, or 'quit' to exit.")

                elif self.state == self.STATE_FAILED:
                    self.show_failed()
                    print("\nPress ENTER to consult again, or 'quit' to exit.")
        finally:
            print("[SIMULATOR] Stopping sensors...")
            self.sensor.stop()


if __name__ == "__main__":
    sim = OracleSimulator()
    sim.run()
