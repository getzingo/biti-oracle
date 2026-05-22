import os
import sys
import signal

from utils.oracle_helpers.oracle_menu import *
from utils.sensor_manager import SensorManager
from utils.config import config
from utils.classes.Fortune import Fortune
from utils.oracle_helpers.generating_helpers import start_fortune_generation

########
# Init

if os.getenv("BOARD") == "raspi":
    print("Running on Raspberry Pi, all configured sensors are used")



SCREEN_WIDTH = pygame_config["pygame-config"]["SCREEN_WIDTH"]
SCREEN_HEIGHT = pygame_config["pygame-config"]["SCREEN_HEIGHT"]
FPS = pygame_config["pygame-config"]["FPS"]
FULLSCREEN = pygame_config["pygame-config"]["FULLSCREEN"]
DEV_MODE = config.dev_mode

COLORS = {name: tuple(rgb) for name, rgb in pygame_config['COLORS'].items()}

class OracleApp:
    # States
    STATE_IDLE = "idle"
    STATE_SENSING = "sensing"
    STATE_GENERATING = "generating"
    STATE_FORTUNE = "fortune"
    STATE_FAILED = "failed"
    def __init__(self):


        pygame.init()

        flags = pygame.FULLSCREEN if FULLSCREEN else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption("The Oracle of Selphi")
        self.clock = pygame.time.Clock()
        self.last_phase = 0


        self.font_title = pygame.font.Font("PressStart2P-Regular.ttf", 32)
        self.font_sub = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)

        # Pre-render static assets
        self.bg = create_gradient_bg()
        self.stars = [Star() for _ in range(80)]
        # Sensing variables
        self.sensing_start_time = 0
        self.sensing_duration = 0
        self.sensing_elapsed = 0
        self.sensing_message_index = 0
        self.sensing_message_timer = 0
        self.sensing_message_alpha = 255  # for fade transitions
        self.msg_index = 0
        self.energy_particles = []
        self.energy_rings = []
        self.sensing_messages = pygame_config["SENSING_MESSAGES"]

        # State Init
        self.state = self.STATE_IDLE
        self.prompt_visible = True
        self.prompt_timer = 0

        self.fortune: Fortune = None
        self.fortune_text: str = ""

        self.fortune_start_time = 0

        # Sensor manager (IR temp sensor on Pi, simulated otherwise)
        self.sensor = SensorManager()
        self.sensor.start()


    def run(self):
        running = True

        # Catch Ctrl+C / SIGTERM gracefully — stop sensors, quit pygame
        def _handle_signal(signum, frame):
            nonlocal running
            print(f"\n[ORACLE] Received signal {signum}, shutting down...")
            running = False
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        while running:
            #dt = self.clock.tick(FPS)
            time_ms = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_SPACE and self.state == self.STATE_IDLE:
                        self.state = self.STATE_SENSING
                        self.sensing_start_time = time_ms
                        print("[ORACLE] Entered sensing state")

            if self.state == self.STATE_IDLE:
                self.draw_idle_screen(time_ms)
                self.fortune_start_time = 0
                # Auto-trigger sensing when hand is detected
                if self.sensor.is_hand_present():
                    self.state = self.STATE_SENSING
                    self.sensing_start_time = time_ms
                    print("[ORACLE] Hand detected — entering sensing state")
            elif self.state == self.STATE_SENSING:

                self.draw_sensing_state(time_ms)
            elif self.state == self.STATE_GENERATING:
                self.draw_generating_state(time_ms)
            elif self.state == self.STATE_FORTUNE:
                self.draw_fortune_state(time_ms)

            pygame.display.flip()

        # ── cleanup ──────────────────────────────────────────────
        print("[ORACLE] Stopping sensors...")
        self.sensor.stop()
        pygame.quit()
        sys.exit()

    def draw_statics(self, time_ms):

        # Background
        self.bg = create_gradient_bg(self.state)
        self.screen.blit(self.bg, (0, 0))
        # Stars
        for star in self.stars:
            star.draw(self.screen, time_ms)
        # Rune deko
        draw_runes(self.screen, time_ms)

    def draw_idle_screen(self, time_ms):

        self.draw_statics(time_ms)
        self.fortune: Fortune = None
        self.fortune_text: str = ""

        draw_pyramid(self.screen, time_ms)

        # Title
        draw_text_centered(self.screen, "DAS ORAKEL VON SELPHI",
                           200, self.font_title, COLORS["gold"])

        draw_line(self.screen)

        # Crystal Ball
        ball_y = 340
        draw_crystal_ball(self.screen, SCREEN_WIDTH // 2, ball_y, 50, time_ms)

        # Debug text
        if DEV_MODE:
            draw_debug_info(self.screen, "PRESS SPACE TO START READING", font=self.font_sub)


        # Blinking prompt text
        if (time_ms // 700) % 2 == 0:
            draw_text_centered(self.screen, "~ Bitte Hand auflegen ~",
                               430, self.font_sub, COLORS["cyan"])

        # Footer
        draw_text_centered(self.screen, "Selfie des Schicksals...",
                           SCREEN_HEIGHT - 150, self.font_small, COLORS["purple"])

        draw_bgld_logo(self.screen)

    def draw_sensing_state(self, time_ms):
        if DEV_MODE:
            draw_debug_info(self.screen, None, font=self.font_sub)
        self.draw_statics(time_ms)
        sensing_max_duration = config.sensing_max_duration_seconds * 1000
        sensing_min_duration = config.sensing_min_duration_seconds * 1000
        elapsed = time_ms - self.sensing_start_time

        base_radius = 50
        pulse = math.sin(elapsed / 600) * 12 + math.sin(elapsed / 230) * 4
        orb_radius = base_radius + int(pulse)
        draw_crystal_ball(self.screen, SCREEN_WIDTH // 2, 280, orb_radius, time_ms)

        phase = time_ms // 2000
        if phase != self.last_phase:
            self.msg_index = random.randint(0, len(self.sensing_messages)-1)
            self.last_phase = phase
        message = self.sensing_messages[self.msg_index]
        alpha = int((math.sin(elapsed / 400) + 1) / 2 * 180 + 60)
        text_surf = self.font_sub.render(message, True, COLORS["cyan"])
        text_surf.set_alpha(alpha)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, 400))
        self.screen.blit(text_surf, text_rect)

        if elapsed > sensing_min_duration and self.fortune is None:
            sensor_val = self.sensor.read()
            if DEV_MODE:
                print(f"[SENSOR] value={sensor_val} (mode={'IR' if self.sensor.is_real else 'sim'})")
            self.fortune = start_fortune_generation(sensor_val)

        if elapsed >= sensing_max_duration:
            print(f"Max sensing duration of {sensing_max_duration} ms reached")
            print("[ORACLE] Entered generating state")
            self.state = self.STATE_GENERATING

    def draw_generating_state(self, time_ms):

        if DEV_MODE:
            draw_debug_info(self.screen, None, font=self.font_sub)
        self.draw_statics(time_ms)
        draw_text_centered(self.screen, "THE ORACLE is about to speak ...",
                           200, self.font_title, COLORS["gold"])
        draw_line(self.screen)
        if self.fortune.fortune_ready:
            self.fortune_start_time = time_ms
            print("[ORACLE] Entered fortune state")
            self.state = self.STATE_FORTUNE

    def draw_fortune_state(self, time_ms):
        if DEV_MODE:
            draw_debug_info(self.screen, None, font=self.font_sub)
        self.draw_statics(time_ms)
        elapsed = time_ms - self.fortune_start_time
        draw_text_centered(self.screen, "Your fortune:",
                           100, self.font_sub, COLORS["cyan"])
        draw_text_centered(self.screen, self.fortune.result,
                           300, self.font_title, COLORS["gold"])

        draw_pyramid(self.screen, time_ms, 600)
        draw_bgld_logo(self.screen)

        if elapsed > config.display_fortune_duration_seconds * 1000:
            print("[ORACLE] Entered idle state")
            self.state = self.STATE_IDLE



if __name__ == "__main__":
    app = OracleApp()
    app.run()