import sys, subprocess
import json
import urllib.request
import urllib.request
import zipfile
import os
import shutil

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

UPDATE_FOLDER = "update_temp"
GAME_FOLDER = "."

try:
    import pygame
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"])
    import pygame
import math, random, json, os
from pygame.locals import *

# -------- CONFIGURATION --------
UPDATE_FOLDER = "update_temp"
GAME_FOLDER = "."
VERSION_FILE = "version.json"
CURRENT_VERSION = "1.0.0"
VERSION_URL = "https://raw.githubusercontent.com/Zaranoix/Zaranoix-Tower-Defense-Auto-Update/main/version.json"  # Update with your GitHub raw URL

# -------- UPDATE FUNCTIONS --------
def check_for_update():
    """Fetches the latest version information from GitHub."""
    try:
        with urllib.request.urlopen(VERSION_URL) as response:
            data = response.read().decode("utf-8")
            update_info = json.loads(data)
        latest_version = update_info.get("latest_version", CURRENT_VERSION)
        download_url = update_info.get("download_url", "")

        if latest_version != CURRENT_VERSION:
            print(f"New version found: {latest_version}. Updating now...")
            return latest_version, download_url
    except Exception as e:
        print("Update check failed:", e)
    return None, None

def download_update(download_url):
    """Downloads and extracts the update from GitHub."""
    try:
        if not os.path.exists(UPDATE_FOLDER):
            os.makedirs(UPDATE_FOLDER)

        # Step 1: Download the update file
        update_file_path = os.path.join(UPDATE_FOLDER, "update.zip")
        print("Downloading update...")
        urllib.request.urlretrieve(download_url, update_file_path)

        # Step 2: Extract the zip file
        print("Extracting update...")
        with zipfile.ZipFile(update_file_path, 'r') as zip_ref:
            zip_ref.extractall(UPDATE_FOLDER)

        # Step 3: Replace old files with new ones
        print("Applying update...")
        for item in os.listdir(UPDATE_FOLDER):
            if item != "update.zip":  # Avoid copying the zip file itself
                s = os.path.join(UPDATE_FOLDER, item)
                d = os.path.join(GAME_FOLDER, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)  # Remove old folder
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

        # Step 4: Cleanup
        print("Cleaning up temporary files...")
        shutil.rmtree(UPDATE_FOLDER)

        print("Update successfully applied! Restarting game...")
        os.execv(sys.executable, ['python'] + sys.argv)  # Restart the game
    except Exception as e:
        print("Update failed:", e)

# -------- RUN AUTO-UPDATER --------
new_version, download_url = check_for_update()
if new_version:
    download_update(download_url)

pygame.init()
pygame.font.init()
pygame.mixer.init()

CURRENT_VERSION = "1.0.0"  # Your game’s current version


# ----- GLOBAL CONSTANTS & VARIABLES -----
WIDTH, HEIGHT = 800, 600
FPS = 60
MIN_TOWER_DISTANCE = 35

# Colors
BLACK    = (0, 0, 0)
WHITE    = (255, 255, 255)
GRAY     = (50, 50, 50)
DARKGRAY = (30, 30, 30)
GREEN    = (34, 139, 34)
DIRT     = (120, 100, 70)
BROWN    = (101, 67, 33)
BLUE     = (50, 120, 255)
YELLOW   = (255, 215, 0)
ORANGE   = (255, 140, 0)
RED      = (220, 20, 60)
CYAN     = (0, 255, 255)
MAGENTA  = (255, 0, 255)
DARKRED  = (139, 0, 0)
PURPLE   = (128, 0, 128)
FOG      = (200, 200, 200)

# Game variables
money = 50
health = 200
wave = 0
wave_in_progress = False
wave_timer = 0
wave_delay = 3000
spawn_queue = []
game_mode = "endless"  # or "challenge"
current_tower_type = None
tower_menu_collapsed = False
paused = False
fast_forward = False
SAVE_FILE = "savegame.json"
fullscreen = False
rain_enabled = True
fog_enabled = True
day_time = 0
menu_scroll_offset = 0
menu_scroll_speed = 30
countdown_time = -1
show_controls = False

# For tower tooltip (the targeting system has been removed)
selected_tower = None  # Holds a Tower object if one is clicked
HOVER_RADIUS = 25      # When mouse is near a tower, its range is shown

# For wave banner animation
wave_banner = ""
wave_banner_timer = 0

# Use Arial for HUD/UI
HUD_FONT = pygame.font.SysFont("Arial", 24)

# Create screen and clock
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tower Defense Prototype")
clock = pygame.time.Clock()

# Enemy path (list of points in world coordinates)
road_path = [
    (0, HEIGHT // 2),
    (WIDTH // 4, HEIGHT // 2),
    (WIDTH // 4, HEIGHT // 3),
    (WIDTH // 2, HEIGHT // 3),
    (WIDTH // 2, (2 * HEIGHT) // 3),
    (3 * WIDTH // 4, (2 * HEIGHT) // 3),
    (3 * WIDTH // 4, HEIGHT // 2),
    (WIDTH, HEIGHT // 2)
]

# ----- UTILITY FUNCTIONS -----

CURRENT_VERSION = "1.0.0"  # Your game’s current version


def get_tower_tooltip(tower_type):
    temp = Tower(0, 0, tower_type)
    fire_rate = round(1000 / temp.cooldown, 2) if temp.cooldown else 0
    name = tower_type.capitalize() + " Tower"
    text = f"{name}\nDamage: {temp.damage}\nRange: {temp.range}\nFire Rate: {fire_rate}/sec\nCost: ${temp.cost}"
    return text

def distance_point_to_segment(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax)*dx + (py - ay)*dy) / (dx*dx + dy*dy)))
    projx = ax + t * dx
    projy = ay + t * dy
    return math.hypot(px - projx, py - projy)

def enemy_progress(enemy):
    if enemy.target_index <= 0:
        return 0
    prev = enemy.path[enemy.target_index - 1]
    curr = enemy.path[enemy.target_index]
    seg_length = math.hypot(curr[0] - prev[0], curr[1] - prev[1])
    ratio = 0 if seg_length == 0 else math.hypot(enemy.x - prev[0], enemy.y - prev[1]) / seg_length
    return (enemy.target_index - 1) + ratio

def start_next_wave(current_wave):
    global wave_in_progress, spawn_queue, last_spawn_time, wave_timer, wave_banner, wave_banner_timer, wave
    wave_in_progress = True
    spawn_queue.clear()
    if current_wave == 1:
        spawn_queue = ["basic"]
    elif current_wave == 2:
        spawn_queue = ["basic"] * 2
    elif current_wave == 3:
        spawn_queue = ["basic"] * 4
    elif current_wave == 4:
        spawn_queue = ["basic"] * 4 + ["fast"]
    else:
        extra = current_wave - 4
        enemy_types = ["basic", "fast", "shielded", "teleporting", "swarm", "boss"]
        spawn_queue = [random.choice(enemy_types) for _ in range(4 + extra)]
    last_spawn_time = pygame.time.get_ticks()
    wave_timer = pygame.time.get_ticks()
    wave_banner = f"Wave {current_wave} Incoming!"
    wave_banner_timer = 2000  # banner duration in ms

def toggle_fullscreen():
    global screen, fullscreen
    fade(screen, fade_in=False, duration=300)
    if fullscreen:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        fullscreen = False
    else:
        try:
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        except pygame.error:
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        fullscreen = True
    fade(screen, fade_in=True, duration=300)

def fade(surface, fade_in=True, duration=500):
    w, h = surface.get_size()
    fade_surf = pygame.Surface((w, h))
    fade_surf.fill(BLACK)
    steps = 30
    delay = duration // steps
    for i in range(steps + 1):
        alpha = 255 - int(255 * i / steps) if fade_in else int(255 * i / steps)
        fade_surf.set_alpha(alpha)
        surface.blit(fade_surf, (0, 0))
        pygame.display.update()
        pygame.time.delay(delay)

def draw_rain(surface, dt):
    for _ in range(10):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        length = random.randint(10, 20)
        pygame.draw.line(surface, (180, 180, 255, 100), (x, y), (x, y + length), 1)

def draw_background(surface, dt, cloud_list):
    global day_time
    day_time = pygame.time.get_ticks() % 60000
    brightness = 0.7 + 0.3 * math.sin(2 * math.pi * day_time / 60000)
    grass = (int(GREEN[0] * brightness), int(GREEN[1] * brightness), int(GREEN[2] * brightness))
    surface.fill(grass)
    for _ in range(10):
        x = random.randint(0, WIDTH)
        y = random.randint(HEIGHT - 150, HEIGHT - 110)
        w = random.randint(20, 60)
        h = random.randint(10, 30)
        patch_color = (int(DIRT[0] * brightness), int(DIRT[1] * brightness), int(DIRT[2] * brightness))
        pygame.draw.ellipse(surface, patch_color, (x, y, w, h))
    for _ in range(5):
        rx = random.randint(0, WIDTH)
        ry = random.randint(0, HEIGHT - 150)
        pygame.draw.circle(surface, DARKGRAY, (rx, ry), random.randint(3, 6))
    for cloud in cloud_list:
        cloud['x'] -= cloud['speed'] * dt
        if cloud['x'] < -cloud['w']:
            cloud['x'] = WIDTH
        cloud_surf = pygame.Surface((cloud['w'], cloud['h']), pygame.SRCALPHA)
        for i in range(3):
            a = max(0, 50 - i * 10)
            pygame.draw.ellipse(cloud_surf, (255, 255, 255, a), (i, i, cloud['w'] - 2 * i, cloud['h'] - 2 * i))
        surface.blit(cloud_surf, (cloud['x'], cloud['y']))
    if fog_enabled:
        fog_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fog_surf.fill((FOG[0], FOG[1], FOG[2], 40))
        surface.blit(fog_surf, (0, 0))
    if rain_enabled:
        draw_rain(surface, dt)

def create_clouds(n):
    clouds = []
    for _ in range(n):
        w = random.randint(80, 150)
        h = random.randint(30, 60)
        x = random.randint(0, WIDTH)
        y = random.randint(20, HEIGHT // 3)
        speed = random.uniform(10, 30) / 1000.0
        clouds.append({'x': x, 'y': y, 'w': w, 'h': h, 'speed': speed})
    return clouds

def draw_road(surface, path):
    road_width = 60
    shadow_offset = 4
    if len(path) < 2:
        return
    for i in range(len(path) - 1):
        start = (path[i][0] + shadow_offset, path[i][1] + shadow_offset)
        end = (path[i+1][0] + shadow_offset, path[i+1][1] + shadow_offset)
        pygame.draw.line(surface, DARKGRAY, start, end, road_width)
        pygame.draw.circle(surface, DARKGRAY, start, road_width // 2)
        pygame.draw.circle(surface, DARKGRAY, end, road_width // 2)
    for i in range(len(path) - 1):
        pygame.draw.line(surface, (100, 100, 100), path[i], path[i+1], road_width)
        pygame.draw.circle(surface, (100, 100, 100), path[i], road_width // 2)
        pygame.draw.circle(surface, (100, 100, 100), path[i+1], road_width // 2)
    border_rect = pygame.Rect(0, HEIGHT//2 + road_width//2 - 5, WIDTH, 10)
    pygame.draw.rect(surface, (0, 100, 0), border_rect, border_radius=5)
    for i in range(len(path) - 1):
        sx, sy = path[i]
        ex, ey = path[i+1]
        seg_length = math.hypot(ex - sx, ey - sy)
        if seg_length == 0:
            continue
        dx, dy = (ex - sx) / seg_length, (ey - sy) / seg_length
        num_dashes = int(seg_length // (20 * 2))
        for j in range(num_dashes):
            start_dash = (sx + dx * j * 40, sy + dy * j * 40)
            end_dash = (start_dash[0] + dx * 20, start_dash[1] + dy * 20)
            pygame.draw.line(surface, WHITE, start_dash, end_dash, 4)

def valid_tower_position(x, y, path, margin=40):
    for i in range(len(path) - 1):
        if distance_point_to_segment((x, y), path[i], path[i+1]) < margin:
            return False
    return True

def tower_overlaps(x, y, towers, min_distance=MIN_TOWER_DISTANCE):
    for t in towers:
        if math.hypot(t.x - x, t.y - y) < min_distance:
            return True
    return False

def draw_dashed_circle(surface, color, center, radius, dash_length=10, width=2):
    circumference = 2 * math.pi * radius
    num_dashes = int(circumference // (dash_length * 2))
    for i in range(num_dashes):
        start_angle = (2 * math.pi / num_dashes) * i * 2
        end_angle = start_angle + (dash_length / radius)
        start_point = (center[0] + radius * math.cos(start_angle), center[1] + radius * math.sin(start_angle))
        end_point = (center[0] + radius * math.cos(end_angle), center[1] + radius * math.sin(end_angle))
        pygame.draw.line(surface, color, start_point, end_point, width)

def render_tooltip(text, font, padding=5, line_spacing=4):
    lines = text.splitlines()
    line_surfs = [font.render(line, True, WHITE) for line in lines]
    max_width = max(s.get_width() for s in line_surfs)
    total_height = sum(s.get_height() for s in line_surfs) + line_spacing*(len(line_surfs)-1)
    surf = pygame.Surface((max_width+2*padding, total_height+2*padding), pygame.SRCALPHA)
    surf.fill((0,0,0,200))
    pygame.draw.rect(surf, WHITE, surf.get_rect(), 2)
    y_offset = padding
    for s in line_surfs:
        surf.blit(s, (padding, y_offset))
        y_offset += s.get_height()+line_spacing
    return surf

def draw_tower_selection_menu(surface, mouse_pos):
    global tower_menu_collapsed, current_tower_type, menu_scroll_offset
    toggle_rect = pygame.Rect(10, HEIGHT-90, 80, 40)
    pygame.draw.rect(surface, GRAY, toggle_rect, border_radius=8)
    font = pygame.font.SysFont("Arial", 20)
    toggle_text = "Menu" if tower_menu_collapsed else "Collapse"
    text_toggle = font.render(toggle_text, True, WHITE)
    surface.blit(text_toggle, (toggle_rect.centerx - text_toggle.get_width()//2, toggle_rect.centery - text_toggle.get_height()//2))
    if tower_menu_collapsed:
        return
    menu_rect = pygame.Rect(0, HEIGHT-120, WIDTH, 120)
    menu_surf = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
    pygame.draw.rect(menu_surf, (20,20,20,200), (0,0,WIDTH,120), border_radius=15)
    surface.blit(menu_surf, (0, HEIGHT-120))
    tower_types = [("basic", BLUE), ("sniper", YELLOW), ("aoe", ORANGE),
                   ("freeze", (0,200,255)), ("poison", (100,0,100)),
                   ("laser", (255,50,50)), ("tesla", (255,255,0)), ("artillery", (160,82,45))]
    box_size = 60; gap = 10
    num_towers = len(tower_types)
    content_width = num_towers*(box_size+gap)-gap
    start_x = 150 + menu_scroll_offset; start_y = HEIGHT-90
    boxes = []
    for i, (t_type, color) in enumerate(tower_types):
        rect = pygame.Rect(start_x+i*(box_size+gap), start_y, box_size, box_size)
        boxes.append((rect, t_type, color))
    min_offset = min(0, WIDTH-150-content_width)
    if menu_scroll_offset>0:
        menu_scroll_offset = 0
    elif menu_scroll_offset < min_offset:
        menu_scroll_offset = min_offset
    for rect, t_type, color in boxes:
        pygame.draw.rect(surface, WHITE, rect, 2, border_radius=8)
        if rect.collidepoint(mouse_pos):
            hover = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(hover, (255,255,255,80), (0,0,rect.width,rect.height), border_radius=8)
            surface.blit(hover, rect.topleft)
            tip_text = get_tower_tooltip(t_type)
            tip_font = pygame.font.SysFont("Arial", 16)
            tooltip_surf = render_tooltip(tip_text, tip_font, padding=5, line_spacing=4)
            tooltip_rect = tooltip_surf.get_rect()
            tooltip_rect.midbottom = (rect.centerx, rect.top-5)
            if tooltip_rect.left < 0:
                tooltip_rect.left = 0
            if tooltip_rect.right > WIDTH:
                tooltip_rect.right = WIDTH
            surface.blit(tooltip_surf, tooltip_rect.topleft)
        pygame.draw.circle(surface, color, rect.center, 20)
        if current_tower_type == t_type:
            pygame.draw.rect(surface, YELLOW, rect, 3, border_radius=8)
            sel_text = font.render("Selected", True, YELLOW)
            surface.blit(sel_text, (rect.centerx - sel_text.get_width()//2, rect.top-20))
        temp = Tower(0,0,t_type)
        cost_text = font.render(f"${temp.cost}", True, WHITE)
        surface.blit(cost_text, (rect.centerx - cost_text.get_width()//2, rect.bottom+2))

def draw_hud(surface):
    hud_text = f"Money: ${money}   Health: {health}   Wave: {wave}   Mode: {game_mode}"
    text_surf = HUD_FONT.render(hud_text, True, WHITE)
    box_surf = pygame.Surface((text_surf.get_width()+20, text_surf.get_height()+10), pygame.SRCALPHA)
    pygame.draw.rect(box_surf, (0,0,0,150), box_surf.get_rect(), border_radius=8)
    box_surf.blit(text_surf, (10,5))
    surface.blit(box_surf, (10,10))

def draw_map_thumbnail(surface, rect):
    xs = [p[0] for p in road_path]
    ys = [p[1] for p in road_path]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    scale = min(rect.width/(max_x-min_x), rect.height/(max_y-min_y))*0.9
    offset_x = rect.x + (rect.width - (max_x-min_x)*scale)/2 - min_x*scale
    offset_y = rect.y + (rect.height - (max_y-min_y)*scale)/2 - min_y*scale
    transformed = [(int(p[0]*scale+offset_x), int(p[1]*scale+offset_y)) for p in road_path]
    pygame.draw.lines(surface, (100,100,100), False, transformed, 10)

# Game state for menu and maps
game_state = "menu"
maps = [{"name": "Roadway", "rect": pygame.Rect(100, 150, 200, 200), "unlocked": True},
        {"name": "Map 2", "rect": pygame.Rect(350, 150, 200, 200), "unlocked": False},
        {"name": "Map 3", "rect": pygame.Rect(600, 150, 200, 200), "unlocked": False}]

# ----- CLASSES: TOWER, ENEMY, PROJECTILE, EXPLOSION -----

class Tower:
    def __init__(self, x, y, tower_type="basic"):
        self.x = x
        self.y = y
        self.type = tower_type
        self.level = 1
        self.ability = None  # Placeholder for special abilities
        # (Targeting system removed.)
        if tower_type == "basic":
            self.range = 150; self.cooldown = 1000; self.damage = 10; self.color = BLUE; self.cost = 50
        elif tower_type == "sniper":
            self.range = 250; self.cooldown = 2000; self.damage = 20; self.color = YELLOW; self.cost = 75
        elif tower_type == "aoe":
            self.range = 120; self.cooldown = 1500; self.damage = 15; self.color = ORANGE; self.cost = 80
        elif tower_type == "freeze":
            self.range = 130; self.cooldown = 1800; self.damage = 8; self.color = (0,200,255); self.cost = 90
        elif tower_type == "poison":
            self.range = 140; self.cooldown = 1700; self.damage = 12; self.color = (100,0,100); self.cost = 100
        elif tower_type == "laser":
            self.range = 240; self.cooldown = 1500; self.damage = 25; self.color = (255,50,50); self.cost = 120
        elif tower_type == "tesla":
            self.range = 160; self.cooldown = 1300; self.damage = 30; self.color = (255,255,0); self.cost = 150
        elif tower_type == "artillery":
            self.range = 300; self.cooldown = 2500; self.damage = 35; self.color = (160,82,45); self.cost = 180
        self.last_shot = pygame.time.get_ticks() - self.cooldown
        self.turret_angle = 0
        self.muzzle_flash_timer = 0

    def update(self, enemies):
        now = pygame.time.get_ticks()
        target = None
        # Simple targeting: select the first enemy in range
        for enemy in enemies:
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            if math.hypot(dx, dy) <= self.range and enemy.health > 0:
                target = enemy
                break
        if target:
            desired_angle = math.atan2(target.y - self.y, target.x - self.x)
            self.turret_angle = desired_angle
            if now - self.last_shot >= self.cooldown:
                self.last_shot = now
                self.muzzle_flash_timer = 100
                proj = Projectile(self.x, self.y, target, self.damage, self.type)
                proj.ability = self.ability
                projectiles.append(proj)
        if self.muzzle_flash_timer > 0:
            self.muzzle_flash_timer -= clock.get_time()

    def upgrade(self):
        global money
        if self.type == "basic" and self.level == 1:
            cost = 10
            if money >= cost:
                money -= cost
                self.level = 2
                self.damage = 15       # Increase damage from 10 to 15
                self.cooldown = 667    # ~1.5 shots per second
                r, g, b = self.color
                self.color = (min(255, r + 20), min(255, g + 20), min(255, b + 20))
                self.ability = "burning"  # placeholder ability
            else:
                print("Not enough coins for upgrade!")
        else:
            upgrade_cost = 50 * self.level
            if money >= upgrade_cost and self.level < 5:
                money -= upgrade_cost
                self.level += 1
                self.damage = int(self.damage * 1.02)
                self.range = int(self.range * 1.02)
                self.cooldown = int(self.cooldown * 0.98)
                r, g, b = self.color
                self.color = (min(255, r + 10), min(255, g + 10), min(255, b + 10))

    def draw(self, surface):
        base_radius = 20
        turret_radius = 10
        points = []
        for i in range(8):
            angle = math.radians(45 * i)
            px = self.x + base_radius * math.cos(angle)
            py = self.y + base_radius * math.sin(angle)
            points.append((px, py))
        pygame.draw.polygon(surface, self.color, points)
        pygame.draw.polygon(surface, BLACK, points, 2)
        pygame.draw.circle(surface, DARKGRAY, (int(self.x), int(self.y)), turret_radius)
        barrel_length = 25
        barrel_width = 6
        bx = self.x + barrel_length * math.cos(self.turret_angle)
        by = self.y + barrel_length * math.sin(self.turret_angle)
        perp_x = (barrel_width / 2) * math.sin(self.turret_angle)
        perp_y = (barrel_width / 2) * -math.cos(self.turret_angle)
        p1 = (self.x - perp_x, self.y - perp_y)
        p2 = (self.x + perp_x, self.y + perp_y)
        p3 = (bx + perp_x, by + perp_y)
        p4 = (bx - perp_x, by - perp_y)
        pygame.draw.polygon(surface, BLACK, [p1, p2, p3, p4])
        if self.muzzle_flash_timer > 0:
            pygame.draw.circle(surface, YELLOW, (int(bx), int(by)), 8)

        # Improved Upgrade Visual:
        if self.level > 1:
            # Create a pulsating outer ring (a golden glow)
            pulse = (math.sin(pygame.time.get_ticks() / 200) + 1) * 0.5  # fluctuates between 0 and 1
            glow_radius = 30 + int(5 * pulse)
            glow_alpha = int(150 + 50 * pulse)
            glow_color = (255, 215, 0, glow_alpha)  # golden color with varying alpha
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius, 4)
            surface.blit(glow_surf, (int(self.x - glow_radius), int(self.y - glow_radius)))
            
            # Display the current upgrade level in the center of the tower
            level_text = pygame.font.SysFont("Arial", 16, bold=True).render(str(self.level), True, WHITE)
            surface.blit(level_text, (self.x - level_text.get_width() // 2, self.y - level_text.get_height() // 2))

class Enemy:
    def __init__(self, path):
        self.path = path
        self.x, self.y = path[0]
        self.target_index = 1
        self.speed = 0.05
        self.health = 20
        self.max_health = self.health
        self.size = 12
        self.color = RED
        self.bob_phase = random.uniform(0, 2 * math.pi)
        self.bob_offset = 0
        self.reward = 5
        self.hit_timer = 0
    def update(self, dt):
        if self.target_index >= len(self.path):
            return
        tx, ty = self.path[self.target_index]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            move = self.speed * dt
            if move >= dist:
                self.x, self.y = tx, ty
                self.target_index += 1
            else:
                self.x += dx / dist * move
                self.y += dy / dist * move
        self.bob_offset = math.sin(pygame.time.get_ticks() / 300 + self.bob_phase) * 3
        if self.hit_timer > 0:
            self.hit_timer -= dt
    def draw(self, surface):
        shadow_surf = pygame.Surface((self.size * 2, self.size), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (0, 0, self.size * 2, self.size // 2))
        surface.blit(shadow_surf, (self.x - self.size, self.y - self.size // 2 + 10))
        col = WHITE if self.hit_timer > 0 else self.color
        pygame.draw.circle(surface, col, (int(self.x), int(self.y + self.bob_offset)), self.size)
        mx, my = pygame.mouse.get_pos()
        if math.hypot(mx - self.x, my - (self.y + self.bob_offset)) < 50:
            bar_w = self.size * 2
            bar_h = 6
            ratio = self.health / self.max_health
            border = pygame.Rect(self.x - self.size, self.y - self.size - 20, bar_w, bar_h)
            pygame.draw.rect(surface, WHITE, border, 1, border_radius=3)
            inner = pygame.Rect(self.x - self.size + 1, self.y - self.size - 20 + 1, int((bar_w - 2) * ratio), bar_h - 2)
            for i in range(inner.width):
                grad = (int(255 * (1 - i / inner.width)), int(255 * (i / inner.width)), 0)
                pygame.draw.line(surface, grad, (inner.x + i, inner.y), (inner.x + i, inner.y + inner.height))
    def is_finished(self):
        return self.target_index >= len(self.path)

class FastEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.speed = 0.08
        self.health = 10
        self.max_health = self.health
        self.size = 10
        self.color = ORANGE
        self.reward = 1

class ArmoredEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.speed = 0.04
        self.health = 40
        self.max_health = self.health
        self.size = 16
        self.color = DARKRED
        self.reward = 10

class BossEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.speed = 0.02
        self.health = 100
        self.max_health = self.health
        self.size = 30
        self.color = PURPLE
        self.reward = 100
        self.heal_timer = 5000  # heal every 5 seconds
    def update(self, dt):
        super().update(dt)
        self.heal_timer -= dt
        if self.heal_timer <= 0:
            for enemy in enemies:
                if enemy != self and math.hypot(enemy.x - self.x, enemy.y - self.y) < 100:
                    enemy.health = min(enemy.max_health, enemy.health + 5)
            self.heal_timer = 5000

class ShieldedEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.speed = 0.04
        self.health = 40
        self.max_health = self.health
        self.shield = 20
        self.size = 16
        self.color = DARKRED
        self.reward = 10

class TeleportingEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.speed = 0.05
        self.health = 20
        self.max_health = self.health
        self.size = 12
        self.color = MAGENTA
        self.reward = 7
        self.teleport_cooldown = 3000
        self.teleport_timer = 3000
    def update(self, dt):
        self.teleport_timer -= dt
        if self.teleport_timer <= 0:
            if self.target_index < len(self.path)-1:
                self.x, self.y = self.path[self.target_index+1]
                self.target_index += 2
            self.teleport_timer = 3000
        super().update(dt)

class SwarmEnemy(Enemy):
    def __init__(self, path):
        super().__init__(path)
        self.speed = 0.07
        self.health = 5
        self.max_health = self.health
        self.size = 8
        self.color = ORANGE
        self.reward = 1

class Projectile:
    def __init__(self, x, y, target, damage, tower_type):
        self.x = x
        self.y = y
        self.target = target
        self.damage = damage
        self.tower_type = tower_type
        self.speed = 0.3
        self.ability = None
        if tower_type == "basic":
            self.color = BLACK; self.size = 5
        elif tower_type == "sniper":
            self.color = CYAN; self.size = 3
        elif tower_type == "aoe":
            self.color = MAGENTA; self.size = 7
        elif tower_type == "freeze":
            self.color = (0,200,255); self.size = 5
        elif tower_type == "poison":
            self.color = (100,0,100); self.size = 5
        elif tower_type == "laser":
            self.color = (255,50,50); self.size = 4
        elif tower_type == "tesla":
            self.color = (255,255,0); self.size = 4
        elif tower_type == "artillery":
            self.color = (160,82,45); self.size = 8
        self.trail = []
    def update(self, dt):
        if self.target.health <= 0:
            return True
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.speed * dt:
            self.target.health -= self.damage
            self.target.hit_timer = 200
            if self.ability == "burning":
                self.target.burning_timer = 1000
                self.target.burn_rate = 5
            explosions.append(Explosion(self.x, self.y, self.color))
            return True
        else:
            self.x += dx / dist * self.speed * dt
            self.y += dy / dist * self.speed * dt
            self.trail.append((self.x, self.y))
            if len(self.trail) > 10:
                self.trail.pop(0)
            return False
    def draw(self, surface):
        if len(self.trail) > 1:
            for i in range(len(self.trail) - 1):
                alpha = int(255 * (i / len(self.trail)))
                col = (self.color[0], self.color[1], self.color[2], alpha)
                pygame.draw.line(surface, col, self.trail[i], self.trail[i+1], 2)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size)

class Explosion:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.particles = []
        for _ in range(20):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(0.1, 0.3)
            self.particles.append({'x': x, 'y': y, 'vx': math.cos(angle)*speed, 'vy': math.sin(angle)*speed, 'life': random.randint(300,600)})
    def update(self, dt):
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt
        self.particles = [p for p in self.particles if p['life'] > 0]
        return len(self.particles) == 0
    def draw(self, surface):
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p['life'] / 600))))
            s = pygame.Surface((4,4), pygame.SRCALPHA)
            s.fill((self.color[0], self.color[1], self.color[2], alpha))
            surface.blit(s, (p['x'], p['y']))

def airstrike():
    global enemies, explosions
    mx, my = pygame.mouse.get_pos()
    for enemy in enemies:
        if math.hypot(enemy.x - mx, enemy.y - my) < 100:
            enemy.health -= 50
            explosions.append(Explosion(enemy.x, enemy.y, RED))

def emp_shockwave():
    global enemies
    for enemy in enemies:
        enemy.speed *= 0.5
    pygame.time.set_timer(USEREVENT + 1, 1000)

def barrier_shield():
    for enemy in enemies:
        enemy.x -= 10
        enemy.y -= 10

def save_game():
    state = {"money": money, "health": health, "wave": wave, "towers": [{"x": t.x, "y": t.y, "type": t.type, "level": t.level} for t in towers]}
    with open(SAVE_FILE, "w") as f:
        json.dump(state, f)

def load_game():
    global money, health, wave, towers, enemies
    try:
        with open(SAVE_FILE, "r") as f:
            state = json.load(f)
        money = state["money"]
        health = state["health"]
        wave = state["wave"]
        towers.clear()
        for t in state["towers"]:
            new_t = Tower(t["x"], t["y"], t["type"])
            new_t.level = t["level"]
            towers.append(new_t)
        enemies.clear()
    except Exception as e:
        print("Load failed:", e)

# ----- GAME OBJECTS & INITIAL SETUP -----
towers = []
enemies = []
projectiles = []
explosions = []
clouds = create_clouds(5)
spawn_queue = []
placing_tower = False
preview_pos = (0, 0)
last_spawn_time = pygame.time.get_ticks()
spawn_delay = 500
wave_message_duration = 2000
wave_message_time = 0

# ----- MAIN GAME LOOP -----
while True:
    dt = clock.tick(FPS)
    current_time = pygame.time.get_ticks()

    if game_state in ("menu", "map_selector", "playing", "game_over"):
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if game_state == "menu":
                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    start_button_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 50, 200, 50)
                    if start_button_rect.collidepoint(mx, my):
                        game_state = "map_selector"
            elif game_state == "map_selector":
                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    for m in maps:
                        if m["rect"].collidepoint(mx, my):
                            if m["unlocked"]:
                                countdown_time = 5000
                                if game_mode == "challenge":
                                    money = 20
                                    health = 100
                                game_state = "playing"
                            break
            elif game_state in ("playing", "game_over"):
                if event.type == KEYDOWN:
                    if event.key == K_h:
                        show_controls = not show_controls
                    if event.key == K_f:
                        toggle_fullscreen()
                    elif event.key == K_p:
                        paused = not paused
                    elif event.key == K_q:
                        current_tower_type = None
                        selected_tower = None
                    elif event.key == K_a:
                        airstrike()
                    elif event.key == K_e:
                        emp_shockwave()
                    elif event.key == K_b:
                        barrier_shield()
                    elif event.key == K_s and (pygame.key.get_mods() & KMOD_SHIFT):
                        save_game()
                    elif event.key == K_l and (pygame.key.get_mods() & KMOD_SHIFT):
                        load_game()
                    elif event.key == K_g:
                        fast_forward = True
                elif event.type == KEYUP:
                    if event.key == K_g:
                        fast_forward = False
                    elif event.type == USEREVENT+1:
                        for enemy in enemies:
                            enemy.speed *= 2
                elif event.type == MOUSEMOTION:
                    preview_pos = event.pos
                    placing_tower = True
                elif event.type == MOUSEWHEEL:
                    menu_scroll_offset += event.y * menu_scroll_speed
                    tower_types = [("basic", BLUE), ("sniper", YELLOW), ("aoe", ORANGE),
                                     ("freeze", (0,200,255)), ("poison", (100,0,100)),
                                     ("laser", (255,50,50)), ("tesla", (255,255,0)),
                                     ("artillery", (160,82,45))]
                    num_towers = len(tower_types)
                    box_size = 60; gap = 10
                    content_width = num_towers*(box_size+gap)-gap
                    min_offset = min(0, WIDTH-150-content_width)
                    if menu_scroll_offset > 0:
                        menu_scroll_offset = 0
                    elif menu_scroll_offset < min_offset:
                        menu_scroll_offset = min_offset
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mx, my = event.pos
                        # If a tower tooltip is open, check for Sell/Upgrade button clicks.
                        if selected_tower is not None:
                            tooltip_x = selected_tower.x + 30
                            tooltip_y = selected_tower.y - 80
                            sell_button_rect = pygame.Rect(tooltip_x + 20, tooltip_y + 100, 80, 40)
                            upgrade_button_rect = pygame.Rect(tooltip_x + 120, tooltip_y + 100, 80, 40)
                            if sell_button_rect.collidepoint(mx, my):
                                money += selected_tower.cost // 2
                                towers.remove(selected_tower)
                                selected_tower = None
                                continue
                            elif upgrade_button_rect.collidepoint(mx, my):
                                selected_tower.upgrade()
                                selected_tower = None
                                continue
                        # Process clicks in the tower menu area.
                        if my >= HEIGHT - 100:
                            toggle_rect = pygame.Rect(10, HEIGHT - 90, 80, 40)
                            if toggle_rect.collidepoint(mx, my):
                                tower_menu_collapsed = not tower_menu_collapsed
                            elif not tower_menu_collapsed:
                                boxes = [(pygame.Rect(150, HEIGHT - 90, 60, 60), "basic"),
                                         (pygame.Rect(220, HEIGHT - 90, 60, 60), "sniper"),
                                         (pygame.Rect(290, HEIGHT - 90, 60, 60), "aoe"),
                                         (pygame.Rect(360, HEIGHT - 90, 60, 60), "freeze"),
                                         (pygame.Rect(430, HEIGHT - 90, 60, 60), "poison"),
                                         (pygame.Rect(500, HEIGHT - 90, 60, 60), "laser"),
                                         (pygame.Rect(570, HEIGHT - 90, 60, 60), "tesla"),
                                         (pygame.Rect(640, HEIGHT - 90, 60, 60), "artillery")]
                                for rect, t_type in boxes:
                                    if rect.collidepoint(mx, my):
                                        current_tower_type = t_type
                                        break
                        else:
                            if current_tower_type is not None:
                                cost_mapping = {"basic": 50, "sniper": 75, "aoe": 80,
                                                "freeze": 90, "poison": 100, "laser": 120,
                                                "tesla": 150, "artillery": 180}
                                cost = cost_mapping.get(current_tower_type, 0)
                                if valid_tower_position(mx, my, road_path) and not tower_overlaps(mx, my, towers) and money >= cost:
                                    money -= cost
                                    towers.append(Tower(mx, my, current_tower_type))
                                    current_tower_type = None
                            else:
                                tower_clicked = None
                                for t in towers:
                                    if math.hypot(t.x - mx, t.y - my) < 20:
                                        tower_clicked = t
                                        break
                                selected_tower = tower_clicked

    if paused:
        continue
    speed_mult = 3 if fast_forward else 1
    dt *= speed_mult
    if game_state == "playing" and countdown_time > 0:
        countdown_time -= dt
        if countdown_time <= 0 and wave == 0:
            wave = 1
            start_next_wave(wave)
    if game_state == "playing":
        if countdown_time <= 0:
            if spawn_queue and current_time - last_spawn_time >= spawn_delay:
                etype = spawn_queue.pop(0)
                if etype == "basic":
                    new_enemy = Enemy(road_path)
                elif etype == "fast":
                    new_enemy = FastEnemy(road_path)
                elif etype == "armored":
                    new_enemy = ArmoredEnemy(road_path)
                elif etype == "shielded":
                    new_enemy = ShieldedEnemy(road_path)
                elif etype == "teleporting":
                    new_enemy = TeleportingEnemy(road_path)
                elif etype == "swarm":
                    new_enemy = SwarmEnemy(road_path)
                elif etype == "boss":
                    new_enemy = BossEnemy(road_path)
                else:
                    new_enemy = Enemy(road_path)
                enemies.append(new_enemy)
                last_spawn_time = current_time
            for t in towers:
                t.update(enemies)
            for e in enemies[:]:
                e.update(dt)
                if e.is_finished():
                    health -= e.health
                    enemies.remove(e)
                elif e.health <= 0:
                    money += e.reward
                    explosions.append(Explosion(e.x, e.y, e.color))
                    enemies.remove(e)
            for p in projectiles[:]:
                if p.update(dt):
                    projectiles.remove(p)
            for ex in explosions[:]:
                if ex.update(dt):
                    explosions.remove(ex)
            if not enemies and not spawn_queue:
                if wave_in_progress:
                    wave_in_progress = False
                    wave_timer = current_time
                elif current_time - wave_timer > wave_delay:
                    wave += 1
                    start_next_wave(wave)
    if health <= 0 and game_state == "playing":
        game_state = "game_over"
    if game_state == "menu":
        screen.fill(BLACK)
        title_text = pygame.font.SysFont("Arial", 72).render("Tower Defense", True, WHITE)
        subtitle_text = pygame.font.SysFont("Arial", 36).render("Made By: You", True, WHITE)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 150))
        screen.blit(subtitle_text, (WIDTH//2 - subtitle_text.get_width()//2, HEIGHT//2 - 80))
        start_button_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 50, 200, 50)
        pygame.draw.rect(screen, GRAY, start_button_rect, border_radius=8)
        button_text = pygame.font.SysFont("Arial", 32).render("Start", True, WHITE)
        screen.blit(button_text, (start_button_rect.centerx - button_text.get_width()//2, start_button_rect.centery - button_text.get_height()//2))
    elif game_state == "map_selector":
        screen.fill((50,50,50))
        selector_text = pygame.font.SysFont("Arial", 48).render("Map Selector", True, WHITE)
        screen.blit(selector_text, (WIDTH//2 - selector_text.get_width()//2, 20))
        for m in maps:
            rect = m["rect"]
            pygame.draw.rect(screen, DARKGRAY, rect, border_radius=8)
            if m["unlocked"]:
                draw_map_thumbnail(screen, rect)
                name_text = pygame.font.SysFont("Arial", 24).render(m["name"], True, WHITE)
                screen.blit(name_text, (rect.centerx - name_text.get_width()//2, rect.bottom - name_text.get_height() - 5))
            else:
                locked_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                locked_overlay.fill((0,0,0,150))
                screen.blit(locked_overlay, rect.topleft)
                lock_text = pygame.font.SysFont("Arial", 24).render("Locked", True, RED)
                screen.blit(lock_text, (rect.centerx - lock_text.get_width()//2, rect.centery - lock_text.get_height()//2))
    elif game_state in ("playing", "game_over"):
        draw_background(screen, dt, clouds)
        draw_road(screen, road_path)
        for t in towers:
            t.draw(screen)
        mx, my = pygame.mouse.get_pos()
        for t in towers:
            if t == selected_tower or math.hypot(t.x - mx, t.y - my) < HOVER_RADIUS:
                draw_dashed_circle(screen, t.color, (int(t.x), int(t.y)), t.range, dash_length=10, width=2)
        if selected_tower is not None:
            tooltip_x = selected_tower.x + 30
            tooltip_y = selected_tower.y - 80
            tooltip_width = 220
            tooltip_height = 150
            tooltip_surf = pygame.Surface((tooltip_width, tooltip_height), pygame.SRCALPHA)
            tooltip_surf.fill((0, 0, 0, 200))
            pygame.draw.rect(tooltip_surf, WHITE, tooltip_surf.get_rect(), 2)
            name_font = pygame.font.SysFont("Arial", 16)
            tower_name = f"{selected_tower.type.capitalize()} Tower"
            damage_text = f"Damage: {selected_tower.damage}"
            fire_rate = round(1000 / selected_tower.cooldown, 2) if selected_tower.cooldown else 0
            fire_rate_text = f"Fire Rate: {fire_rate}/sec"
            dps = round(selected_tower.damage * fire_rate, 2)
            dps_text = f"DPS: {dps}"
            # (No targeting mode text since it was removed)
            tooltip_surf.blit(name_font.render(tower_name, True, WHITE), (10, 10))
            tooltip_surf.blit(name_font.render(damage_text, True, WHITE), (10, 30))
            tooltip_surf.blit(name_font.render(fire_rate_text, True, WHITE), (10, 50))
            tooltip_surf.blit(name_font.render(dps_text, True, WHITE), (10, 70))
            sell_button_rect = pygame.Rect(20, 100, 80, 40)
            upgrade_button_rect = pygame.Rect(120, 100, 80, 40)
            pygame.draw.rect(tooltip_surf, DARKRED, sell_button_rect)
            sell_text = name_font.render("Sell", True, WHITE)
            tooltip_surf.blit(sell_text, (sell_button_rect.centerx - sell_text.get_width()//2,
                                          sell_button_rect.centery - sell_text.get_height()//2))
            pygame.draw.rect(tooltip_surf, GREEN, upgrade_button_rect)
            upgrade_text = name_font.render("Upgrade", True, WHITE)
            tooltip_surf.blit(upgrade_text, (upgrade_button_rect.centerx - upgrade_text.get_width()//2,
                                             upgrade_button_rect.centery - upgrade_text.get_height()//2))
            screen.blit(tooltip_surf, (tooltip_x, tooltip_y))
        if placing_tower and preview_pos[1] < HEIGHT - 100 and current_tower_type is not None:
            mx, my = preview_pos
            valid = valid_tower_position(mx, my, road_path) and not tower_overlaps(mx, my, towers)
            tower_colors = {"basic": BLUE, "sniper": YELLOW, "aoe": ORANGE,
                            "freeze": (0,200,255), "poison": (100,0,100),
                            "laser": (255,50,50), "tesla": (255,255,0),
                            "artillery": (160,82,45)}
            range_values = {"basic": 150, "sniper": 250, "aoe": 120,
                            "freeze": 130, "poison": 140, "laser": 240,
                            "tesla": 160, "artillery": 300}
            preview_color = tower_colors.get(current_tower_type, WHITE)
            range_val = range_values.get(current_tower_type, 150)
            if not valid:
                preview_color = (255, 0, 0)
            aura_surf = pygame.Surface((range_val * 2 + 10, range_val * 2 + 10), pygame.SRCALPHA)
            draw_dashed_circle(aura_surf, preview_color, (range_val + 5, range_val + 5), range_val, dash_length=10, width=2)
            rect = aura_surf.get_rect(center=(mx, my))
            screen.blit(aura_surf, rect.topleft)
            pygame.draw.circle(screen, preview_color, (mx, my), 15)
        for e in enemies:
            e.draw(screen)
        for p in projectiles:
            p.draw(screen)
        for ex in explosions:
            ex.draw(screen)
        draw_tower_selection_menu(screen, pygame.mouse.get_pos())
        draw_hud(screen)
        hint_text = pygame.font.SysFont("Arial", 20).render("Press H to see controls", True, WHITE)
        screen.blit(hint_text, (WIDTH - hint_text.get_width() - 10, 10))
        if show_controls:
            controls_lines = [
                "Controls:",
                "H: Toggle this help",
                "F: Toggle fullscreen",
                "P: Pause",
                "Q: Deselect tower",
                "A: Airstrike",
                "E: EMP shockwave",
                "B: Barrier shield",
                "Shift+S: Save game",
                "Shift+L: Load game",
                "G: Fast forward",
                "Left Click (menu): Select tower",
                "Left Click (play area): Place tower",
                "Right Click: Upgrade tower",
                "Shift+Right Click: Sell tower"
            ]
            control_font = pygame.font.SysFont("Arial", 18)
            line_surfs = [control_font.render(line, True, WHITE) for line in controls_lines]
            overlay_width = max(s.get_width() for s in line_surfs) + 20
            overlay_height = sum(s.get_height() for s in line_surfs) + 10*(len(line_surfs)-1) + 20
            overlay_surf = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
            overlay_surf.fill((0,0,0,200))
            pygame.draw.rect(overlay_surf, WHITE, overlay_surf.get_rect(), 2)
            y_offset = 10
            for s in line_surfs:
                overlay_surf.blit(s, (10, y_offset))
                y_offset += s.get_height() + 10
            overlay_x = WIDTH - overlay_width - 10
            overlay_y = 10 + hint_text.get_height() + 5
            screen.blit(overlay_surf, (overlay_x, overlay_y))
        if game_state == "playing" and countdown_time > 0:
            seconds_left = max(0, int((countdown_time + 999) // 1000))
            minutes = seconds_left // 60
            seconds = seconds_left % 60
            time_str = f"{minutes}:{seconds:02d}"
            countdown_text = pygame.font.SysFont("Arial", 120).render(time_str, True, RED)
            screen.blit(countdown_text, (WIDTH//2 - countdown_text.get_width()//2, HEIGHT//2 - countdown_text.get_height()//2))
        elif game_state == "playing" and countdown_time <= 0 and current_time - wave_timer < wave_message_duration:
            wave_text = pygame.font.SysFont("Arial", 48).render(wave_banner, True, RED)
            screen.blit(wave_text, (WIDTH//2 - wave_text.get_width()//2, 50))
        if game_state == "game_over":
            game_over_text = pygame.font.SysFont("Arial", 100).render("GAME OVER", True, RED)
            screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, HEIGHT//2 - game_over_text.get_height()//2))
    pygame.display.flip()
pygame.quit()
sys.exit()
