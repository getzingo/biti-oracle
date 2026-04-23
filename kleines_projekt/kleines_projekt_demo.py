import math
import time
import yaml
import RPi.GPIO as GPIO
import board
import adafruit_dht
import pygame

with open("config_klein.yaml", 'r') as f:
    config = yaml.safe_load(f)

SCREEN_WIDTH = config["pygame-config"]["SCREEN_WIDTH"]
SCREEN_HEIGHT = config["pygame-config"]["SCREEN_HEIGHT"]
FPS = config["pygame-config"]["FPS"]
FULLSCREEN = config["pygame-config"]["FULLSCREEN"]

class ProjektKlein:
    STATE_IDLE = "idle"
    STATE_MEASURING = "measuring"

    def __init__(self):
        pygame.init()
        flags = pygame.FULLSCREEN if FULLSCREEN else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags=flags, display=0)
        self.t_secs = 0
        pygame.display.set_caption("Kleines Projekt Demo")

        self.font_title = pygame.font.SysFont("monospace", 60)
        self.font_text = pygame.font.SysFont("monospace", 70)

        self.bg = pygame.Surface(self.screen.get_size())
        self.bob = 0
        self.state = self.STATE_IDLE


        # ultrasonic sensor setup
        self.PIN_TRIG = 16
        self.PIN_ECHO = 12
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PIN_TRIG, GPIO.OUT)
        GPIO.setup(self.PIN_ECHO, GPIO.IN)
        GPIO.output(self.PIN_TRIG, GPIO.LOW)
        time.sleep(0.5)
        self.movement_detection_range = 35.0
        self.movement_detection_interval = 5
        self.stagnated_movement = []

        # DHT11 setup
        self.dht_device = adafruit_dht.DHT11(board.D4)


        self.current_distance = self.get_distance()
        self.baseline_distance = self.current_distance
        self.distance_threshold = 50.0

        self.current_temp = "--"
        self.current_hum = "--"
        self.last_sensor_read = 0

    @staticmethod
    def calibrate_distance(raw_distance: float, measured_50: float = 48.5, measured_100: float = 98.5, max_distance: float = 400.0):
        if raw_distance > max_distance:
            return 0.0
        calibration_points = [
            (0.0, 0.0),
            (measured_50, 50.0),
            (measured_100, 100.0),
        ]

        for d in range(len(calibration_points) - 1):
            raw_low, true_low = calibration_points[d]
            raw_high, true_high = calibration_points[d+1]
            if raw_low <= raw_distance <= raw_high:
                t = (raw_distance - raw_low) / (raw_high - raw_low)
                return round(true_low + t * (true_high - true_low), 2)

        raw_low, true_low = calibration_points[-2]
        raw_high, true_high = calibration_points[-1]
        t = (raw_distance - raw_low) / (raw_high - raw_low)
        return round(true_low + t * (true_high - true_low), 2)

    def movement_detection(self, distance: float) -> bool:
        print(f"Distance: {distance:.2f} cm")
        print(f"Gathered: {self.stagnated_movement}")
        if len(self.stagnated_movement) < self.movement_detection_interval:
            self.stagnated_movement.append(distance)
            return False
        if len(self.stagnated_movement) == self.movement_detection_interval:
            if (max(self.stagnated_movement) - min(self.stagnated_movement)) < self.movement_detection_range and distance > self.distance_threshold + 25.0:
                self.stagnated_movement = []
                return True
        self.stagnated_movement = self.stagnated_movement[1:] + [distance]
        return False


    def get_distance(self):
        # Send 10us pulse to trigger
        GPIO.output(self.PIN_TRIG, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(self.PIN_TRIG, GPIO.LOW)

        pulse_start_time = time.time()
        pulse_end_time = time.time()
        timeout = time.time() + 0.1

        while GPIO.input(self.PIN_ECHO) == 0 and time.time() < timeout:
            pulse_start_time = time.time()

        while GPIO.input(self.PIN_ECHO) == 1 and time.time() < timeout:
            pulse_end_time = time.time()

        pulse_duration = pulse_end_time - pulse_start_time
        distance = round(pulse_duration * 17150, 2)

        if self.state == self.STATE_MEASURING:
            if self.movement_detection(distance):
                self.state = self.STATE_IDLE

        return self.calibrate_distance(distance)

    def read_dht(self):
        try:
            temp = self.dht_device.temperature
            hum = self.dht_device.humidity
            if temp is not None and hum is not None:
                self.current_temp = temp
                self.current_hum = hum
        except RuntimeError as error:
            # Too many errors while reading
            pass

    def draw_centered_text(
            self,
            text: str,
            font: pygame.font.Font = None,
            y_offset: int=0,
            color=(250,250,250)
        ):
        """
        Helper function to draw centered text on screen, font from self.font
        :param text: String text to be drawn
        :param font: Optional pygame.font.Font object
        :param y_offset: Integer offset of y-axis
        :param color: Color of text in RGB tuple
        :return: None
        """
        if not font:
            # normal text
            text_surf = self.font_text.render(text, True, color)
            y = (self.screen.get_height() - text_surf.get_height()) / 2 + self.bob
        else:
            # title text
            text_surf = font.render(text, True, color)
            y = (self.screen.get_height() - text_surf.get_height()) / 2
        x = (self.screen.get_width() - text_surf.get_width()) / 2
        self.screen.blit(text_surf, (x,y + y_offset))


    def draw_idle_screen(self):
        self.screen.fill((15, 15, 15))
        # (delta_time * speed) * amplitude
        self.bob = math.sin(self.t_secs * 1.5) * 10
        self.draw_centered_text("MOBC Demo",font=self.font_title, y_offset=-150)
        self.draw_centered_text("Hand über Sensor halten", y_offset=60)

    def draw_measuring_screen(self):
        self.screen.fill((15, 15, 15))
        self.bob = 0

        # Throttle sensor reads to once every 2 seconds
        current_time = time.time()
        if current_time - self.last_sensor_read > 2.0:
            self.current_distance = self.get_distance()
            self.read_dht()
            self.last_sensor_read = current_time

        self.draw_centered_text("Messung Aktiv", font=self.font_title, y_offset=-200)
        self.draw_centered_text(f"Distanz: {self.current_distance} cm", y_offset=-50)
        self.draw_centered_text(f"Temp: {self.current_temp} C", y_offset=50)
        self.draw_centered_text(f"Luftf: {self.current_hum} %", y_offset=150)

    def run(self):
        running = True
        clock = pygame.time.Clock()
        while running:
            delta_time = clock.tick(FPS) / 1000
            self.t_secs += delta_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_SPACE:
                        self.state = ProjektKlein.STATE_MEASURING
            if self.state == self.STATE_IDLE:
                self.draw_idle_screen()

                # measure when interrupted
                current_distance = self.get_distance()
                if abs(current_distance - self.current_distance) > self.distance_threshold:
                    self.state = self.STATE_MEASURING
                    # reset readout time
                    self.last_sensor_read = 0

            elif self.state == self.STATE_MEASURING:
                self.draw_measuring_screen()

            pygame.display.flip()

        GPIO.cleanup()
        pygame.quit()

if __name__ == "__main__":
    try:
        p = ProjektKlein()
        p.run()
    except KeyboardInterrupt:
        GPIO.cleanup()