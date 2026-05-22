import pygame
import math
import random
import yaml

from utils.oracle_helpers.text_helpers import format_multiline_text

with open("config.yaml") as f:
    pygame_config = yaml.safe_load(f)

SCREEN_WIDTH = pygame_config["pygame-config"]["SCREEN_WIDTH"]
SCREEN_HEIGHT = pygame_config["pygame-config"]["SCREEN_HEIGHT"]
FPS = pygame_config["pygame-config"]["FPS"]

COLORS = {name: tuple(rgb) for name, rgb in pygame_config['COLORS'].items()}

def create_pixel_surface(pixel_data, palette, scale=4) -> pygame.Surface:
    """
    Helper function that creates a pixel surface
    pixel_data: list of lists (rows of ints), 0 = transparent, 1+ = palette index
    palette: dict mapping int -> (r, g, b)
    """
    h = len(pixel_data)
    w = max(len(row) for row in pixel_data)
    surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)

    for y, row in enumerate(pixel_data):
        for x, val in enumerate(row):
            if val == 0:
                continue
            color = palette.get(val, (255, 0, 255))
            pygame.draw.rect(surf, color, (x * scale, y * scale, scale, scale))
    return surf

def draw_crystal_ball(surface, cx, cy, radius, time_ms):
    pulse = math.sin(time_ms / 800) * 0.3 + 0.7
    for i in range(5, 0, -1):
        alpha = int(30 * pulse * (6 - i) / 5)
        glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        glow_color = (*COLORS["orb_glow"], alpha)
        pygame.draw.circle(glow_surf, glow_color,
                           (radius * 2, radius * 2), radius + i * 8)
        surface.blit(glow_surf, (cx - radius * 2, cy - radius * 2))

    # Main orb body
    pygame.draw.circle(surface, COLORS["orb_core"], (cx, cy), radius)

    # Inner swirl
    angle = time_ms / 1000
    for i in range(3):
        a = angle + i * (2.094)  # 120° apart
        hx = cx + int(math.cos(a) * radius * 0.4)
        hy = cy + int(math.sin(a) * radius * 0.4)
        swirl_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(swirl_surf, (*COLORS["magenta"], 60),
                           (radius, radius), radius // 3)
        surface.blit(swirl_surf, (hx - radius, hy - radius))

    # Speculars
    highlight_y = cy - radius // 3
    highlight_x = cx - radius // 4
    pygame.draw.circle(surface, (*COLORS["orb_highlight"], 120),
                       (highlight_x, highlight_y), radius // 5)

    # Orb outline
    pygame.draw.circle(surface, COLORS["purple"], (cx, cy), radius, 2)

    # Base
    base_w = int(radius * 1.4)
    base_h = int(radius * 0.3)
    base_rect = pygame.Rect(cx - base_w // 2, cy + radius - 4, base_w, base_h)
    pygame.draw.rect(surface, COLORS["purple"], base_rect)
    pygame.draw.rect(surface, COLORS["magenta"], base_rect, 2)

EYE_PALETTE = {
    1: COLORS["purple"],
    2: COLORS["eye_white"],
    3: COLORS["eye_iris"],
    4: COLORS["eye_pupil"],
    5: COLORS["cyan"],
    6: COLORS["magenta"],
    7: COLORS["gold"],
}

EYE_PIXELS = [
    [0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0],
    [0,0,0,0,1,1,6,6,6,6,6,6,6,1,1,0,0,0,0],
    [0,0,0,1,6,2,2,2,2,2,2,2,2,2,6,1,0,0,0],
    [0,0,1,6,2,2,2,2,3,3,3,2,2,2,2,6,1,0,0],
    [0,1,6,2,2,2,3,3,3,4,3,3,3,2,2,2,6,1,0],
    [1,6,2,2,2,3,3,3,4,4,4,3,3,3,2,2,2,6,1],
    [0,1,6,2,2,2,3,3,3,4,3,3,3,2,2,2,6,1,0],
    [0,0,1,6,2,2,2,2,3,3,3,2,2,2,2,6,1,0,0],
    [0,0,0,1,6,2,2,2,2,2,2,2,2,2,6,1,0,0,0],
    [0,0,0,0,1,1,6,6,6,6,6,6,6,1,1,0,0,0,0],
    [0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0],
]

# Triangle around eye
TRIANGLE_PALETTE = {
    1: COLORS["gold"],
    2: COLORS["cyan"],
}

TRIANGLE_PIXELS = [
    [0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,1,2,0,2,1,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,1,2,0,0,0,2,1,0,0,0,0,0,0],
    [0,0,0,0,0,1,2,0,0,0,0,0,2,1,0,0,0,0,0],
    [0,0,0,0,1,2,0,0,0,0,0,0,0,2,1,0,0,0,0],
    [0,0,0,1,2,0,0,0,0,0,0,0,0,0,2,1,0,0,0],
    [0,0,1,2,0,0,0,0,0,0,0,0,0,0,0,2,1,0,0],
    [0,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

BURGENLAND_PALETTE = {
    1: (200, 30, 30),    # deep red (outer)
    2: (220, 60, 30),    # red-orange
    3: (235, 100, 25),   # orange
    4: (240, 140, 20),   # warm orange
    5: (250, 180, 30),   # gold-orange
    6: (255, 210, 50),   # yellow core
    7: (255, 230, 100),  # bright yellow highlight
    8: (180, 20, 20),    # darkest red (outline accents)
}

BURGENLAND_PIXELS = [
    [0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
    [0,0,0,0,1,1,2,2,2,2,2,1,1,0,0,0,0],
    [0,0,0,1,2,2,3,3,3,3,2,2,2,1,0,0,0],
    [0,0,1,2,3,3,3,4,4,3,3,3,2,2,1,0,0],
    [0,1,2,3,3,4,4,4,4,4,3,8,2,2,2,1,0],
    [0,1,2,3,4,4,5,5,5,4,8,2,3,3,2,1,0],
    [1,2,3,8,4,5,5,6,6,5,4,3,3,4,3,2,1],
    [1,2,3,8,5,5,6,7,6,5,4,4,4,4,3,2,1],
    [1,2,3,4,8,5,6,6,5,5,5,5,5,4,3,2,1],
    [1,2,3,4,4,8,5,5,5,6,5,5,4,4,3,2,1],
    [0,1,2,3,4,4,8,8,5,5,5,4,4,3,2,1,0],
    [0,1,2,3,3,4,3,3,8,8,4,4,3,3,2,1,0],
    [0,0,1,2,3,3,3,3,3,3,3,3,3,2,1,0,0],
    [0,0,0,1,2,2,3,3,3,3,3,2,2,1,0,0,0],
    [0,0,0,0,1,1,2,2,2,2,2,1,1,0,0,0,0],
    [0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
]


# Starfield
class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.choice([1, 1, 1, 2, 2, 3])
        self.speed = random.uniform(0.5, 2.0)  # twinkle speed
        self.offset = random.uniform(0, math.tau)
        self.color_base = random.choice([
            COLORS["star"], COLORS["cyan"], COLORS["gold"], COLORS["white"]
        ])

    def draw(self, surface, time_ms):
        brightness = (math.sin(time_ms / 1000 * self.speed + self.offset) + 1) / 2
        color = tuple(int(c * (0.3 + 0.7 * brightness)) for c in self.color_base)
        if self.size <= 1:
            surface.set_at((self.x, self.y), color)
        else:
            pygame.draw.rect(surface, color, (self.x, self.y, self.size, self.size))

def draw_text(surface, text, x, y, font, color=COLORS["gold"], shadow=True):
    if text:
        lines = format_multiline_text(text, font, max_width=SCREEN_WIDTH * 7 // 8)
    else:
        return
    line_height = font.get_height() + 2
    for i, line in enumerate(lines):
        line_y = y + i * line_height
        if shadow:
            shadow_color = (color[0] // 4, color[1] // 4, color[2] // 4)
            shadow_surf = font.render(text, False, shadow_color)
            surface.blit(shadow_surf, (x + 2, line_y + 2))
        text_surf = font.render(line, False, color)
        surface.blit(text_surf, (x, line_y))


def draw_text_centered(surface, text, y, font, color=COLORS["gold"], shadow=True):
    if text:
        lines = format_multiline_text(text, font, max_width=SCREEN_WIDTH * 7 // 8)
    else:
        return
    line_height = font.get_height() + 2

    for i, line in enumerate(lines):
        text_surf = font.render(line, False, color)
        line_x = (SCREEN_WIDTH - text_surf.get_width()) // 2
        line_y = y + i * line_height
        _draw_single_text_line(surface, line, line_x, line_y, font, color, shadow)

def _draw_single_text_line(surface, text, x, y, font, color=COLORS["gold"], shadow=True):
    if shadow:
        shadow_color = (color[0] // 4, color[1] // 4, color[2] // 4)
        shadow_surf = font.render(text, False, shadow_color)
        surface.blit(shadow_surf, (x + 2, y + 2))
    text_surf = font.render(text, False, color)
    surface.blit(text_surf, (x, y))

def draw_debug_info(surface, debug_text, font, color=COLORS["gold"]):
    if debug_text:
        info_text = font.render(debug_text, False, color)
        x = (SCREEN_WIDTH - info_text.get_width()) // 2
        y = SCREEN_HEIGHT - 100
        surface.blit(info_text, (x, y))
    disclaimer_x, disclaimer_y = 20, 20
    disclaimer_text = font.render("DEV MODE ON", False, COLORS["white"])
    surface.blit(disclaimer_text, (disclaimer_x, disclaimer_y))


def create_gradient_bg(state="idle") -> pygame.Surface:
    bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    if state == "idle" or state == "generating":
        top_color = COLORS["bg_dark"]
        bottom_color = COLORS["bg_mid"]
    elif state == "sensing" or state == "fortune":
        top_color = COLORS["bg_mid"]
        bottom_color = COLORS["bg_orange"]
    for y in range(SCREEN_HEIGHT):
        t = y / SCREEN_HEIGHT
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    return bg

def draw_runes(surface, time_ms):
    rune_chars = "°~<>*$€@∆-x"
    font_small = pygame.font.Font("RobotoFlex.ttf", 24)

    for i, char in enumerate(rune_chars):
        float_y = math.sin(time_ms / 1500 + i * 0.8) * 10
        alpha = int((math.sin(time_ms / 2000 + i) + 1) / 2 * 180 + 40)

        rune_surf = font_small.render(char, True, COLORS["purple"])
        rune_surf.set_alpha(alpha)

        if i < len(rune_chars) // 2:
            x = 20 + (i % 3) * 15
            y = 60 + i * 50 + float_y
        else:
            x = SCREEN_WIDTH - 50 + (i % 3) * 15
            y = 60 + (i - len(rune_chars) // 2) * 50 + float_y

        surface.blit(rune_surf, (x, y))

def draw_pyramid(surface, time_ms, y_offset = 0):
    triangle_surf = create_pixel_surface(TRIANGLE_PIXELS, TRIANGLE_PALETTE, scale=6)
    eye_surf = create_pixel_surface(EYE_PIXELS, EYE_PALETTE, scale=4)
    triangle_x = (SCREEN_WIDTH - triangle_surf.get_width()) // 2
    triangle_y = 30 + y_offset
    bob = math.sin(time_ms / 2000) * 6
    surface.blit(triangle_surf, (triangle_x, triangle_y + bob))

    eye_x = (SCREEN_WIDTH - eye_surf.get_width()) // 2
    eye_y = 58 + bob + y_offset
    surface.blit(eye_surf, (eye_x, int(eye_y)))

def draw_line(surface):
    line_y = 250
    line_w = 300
    pygame.draw.line(
        surface,
        COLORS["cyan"],
        (SCREEN_WIDTH // 2 - line_w, line_y),
        (SCREEN_WIDTH // 2 + line_w, line_y),
        2
    )

    diamond_size = 6
    cx = SCREEN_WIDTH // 2
    diamond_points = [
            (cx, line_y - diamond_size),
            (cx + diamond_size, line_y),
            (cx, line_y + diamond_size),
            (cx - diamond_size, line_y),
        ]
    pygame.draw.polygon(surface, COLORS["gold"], diamond_points)


def draw_bgld_logo(surface):
    logo = create_pixel_surface(
            BURGENLAND_PIXELS, BURGENLAND_PALETTE, scale=5
        )
    logo_margin = 12
    logo_x = SCREEN_WIDTH - logo.get_width() - logo_margin
    logo_y = SCREEN_HEIGHT - logo.get_height() - logo_margin
    surface.blit(logo, (logo_x, logo_y))
