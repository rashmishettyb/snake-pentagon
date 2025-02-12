import pygame
import sys
import math
import random
import os
import urllib.request
import numpy as np  # Required for generating a fallback beep sound

# --------------------
# Initialization and Window Setup
# --------------------
pygame.init()

# Initialize the mixer for music and sound playback.
pygame.mixer.init()

WIDTH, HEIGHT = 1600, 1600
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake in a Pentagon")

# --------------------
# Music Setup (Exciting Background Music)
# --------------------
music_file = "exciting_music.mp3"
music_url = "http://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

if not os.path.exists(music_file):
    print("Downloading exciting background music...")
    try:
        urllib.request.urlretrieve(music_url, music_file)
        print("Download complete!")
    except Exception as e:
        print("Error downloading music:", e)

try:
    pygame.mixer.music.load(music_file)
    pygame.mixer.music.set_volume(0.5)  # Adjust volume (0.0 to 1.0)
    pygame.mixer.music.play(-1)         # Loop indefinitely
except Exception as e:
    print("Error loading music:", e)

# --------------------
# Boring Sound Setup (For When the Snake Dies)
# --------------------
try:
    boring_file = "boring_sound.wav"
    boring_url = "https://www.soundjay.com/button/sounds/button-10.wav"  # Publicly available WAV file
    if not os.path.exists(boring_file):
        print("Downloading boring death sound...")
        urllib.request.urlretrieve(boring_url, boring_file)
        print("Download complete!")
    boring_sound = pygame.mixer.Sound(boring_file)
except Exception as e:
    print("Error loading boring sound:", e)
    # If downloading/loading fails, generate a simple beep tone as a fallback.
    sample_rate = 44100
    duration = 0.5  # 0.5 seconds beep
    frequency = 300  # 300 Hz frequency
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Generate a sine wave (mono)
    wave = 0.5 * np.sin(2 * math.pi * frequency * t)
    # Convert to 16-bit signed integers
    wave = np.int16(wave * 32767)
    # Duplicate the mono signal into two channels for stereo output
    wave_stereo = np.column_stack((wave, wave))
    boring_sound = pygame.sndarray.make_sound(wave_stereo)

# --------------------
# Colors (RGB)
# --------------------
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
GREEN   = (0, 200, 0)       # Body color
RED     = (200, 0, 0)       # Used for tongue (and death message below)
BLUE    = (0, 0, 200)
YELLOW  = (255, 255, 0)
# A custom color for the inland taipan head (olive-greenish tone)
TAIPAN_HEAD = (100, 140, 50)

# --------------------
# Clock and Game Speed
# --------------------
clock = pygame.time.Clock()
FPS = 5  # Game speed

# --------------------
# Pentagon Setup
# --------------------
PENTAGON_CENTER = (WIDTH // 2, HEIGHT // 2)
PENTAGON_RADIUS = 510  # Distance from center to each vertex
PENTAGON_SIDES  = 5

def get_pentagon_vertices(center, radius, sides):
    """Compute vertices for a regular polygon (here, a pentagon)."""
    vertices = []
    angle_offset = math.radians(-90)  # So one vertex points upward
    for i in range(sides):
        angle = angle_offset + i * (2 * math.pi / sides)
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        vertices.append((x, y))
    return vertices

pentagon_vertices = get_pentagon_vertices(PENTAGON_CENTER, PENTAGON_RADIUS, PENTAGON_SIDES)

def draw_pentagon(surface, vertices, color, width=5):
    """Draw the pentagon boundary."""
    pygame.draw.polygon(surface, color, vertices, width)

# --------------------
# Snake and Food Settings
# --------------------
SEGMENT_SIZE = 20  # Also serves as the snake's grid size and roughly its thickness.

# --------------------
# Head Drawing
# --------------------
def draw_snake_head(surface, head_pos, direction, head_color):
    """
    Draw a realistic snake head (inspired by the inland taipan) with an elliptical shape,
    eyes, and a tongue. The head is drawn on its own surface so it can be rotated to match the movement.
    """
    head_center = (head_pos[0] + SEGMENT_SIZE // 2, head_pos[1] + SEGMENT_SIZE // 2)
    surf_size = SEGMENT_SIZE * 4
    head_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
    
    ellipse_rect = pygame.Rect(surf_size//4, surf_size//3, SEGMENT_SIZE*2, SEGMENT_SIZE)
    pygame.draw.ellipse(head_surf, head_color, ellipse_rect)
    
    # Eyes
    eye_radius = SEGMENT_SIZE // 4
    left_eye_pos  = (int(surf_size * 0.65), int(surf_size * 0.45))
    right_eye_pos = (int(surf_size * 0.65), int(surf_size * 0.55))
    pygame.draw.circle(head_surf, WHITE, left_eye_pos, eye_radius)
    pygame.draw.circle(head_surf, WHITE, right_eye_pos, eye_radius)
    pupil_radius = max(1, eye_radius // 2)
    pygame.draw.circle(head_surf, BLACK, left_eye_pos, pupil_radius)
    pygame.draw.circle(head_surf, BLACK, right_eye_pos, pupil_radius)
    
    # Tongue
    tongue_start = (ellipse_rect.right, ellipse_rect.centery)
    tongue_end   = (ellipse_rect.right + SEGMENT_SIZE//2, ellipse_rect.centery)
    pygame.draw.line(head_surf, RED, tongue_start, tongue_end, 2)
    
    angle = math.degrees(math.atan2(direction[1], direction[0]))
    rotated_head = pygame.transform.rotate(head_surf, -angle)
    rotated_rect = rotated_head.get_rect(center=head_center)
    surface.blit(rotated_head, rotated_rect.topleft)

# --------------------
# Body Drawing
# --------------------
def draw_snake_body(surface, snake, body_color):
    """
    Draw the snake's body as a continuous smooth line.
    (Excludes the head; the head is drawn separately.)
    """
    centers = [(seg[0] + SEGMENT_SIZE//2, seg[1] + SEGMENT_SIZE//2) for seg in snake]
    if len(centers) > 1:
        pygame.draw.lines(surface, body_color, False, centers[1:], SEGMENT_SIZE)
        for center in centers[1:]:
            pygame.draw.circle(surface, body_color, center, SEGMENT_SIZE//2)

def draw_snake(surface, snake, body_color, head_color, direction):
    """
    Draw the complete snake by drawing its body and then its head.
    """
    if len(snake) > 1:
        draw_snake_body(surface, snake, body_color)
    draw_snake_head(surface, snake[0], direction, head_color)

# --------------------
# Food Setup
# --------------------
FOOD_RADIUS = SEGMENT_SIZE // 2

def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside

def spawn_food():
    while True:
        x = random.randint(0, WIDTH - FOOD_RADIUS * 5)
        y = random.randint(0, HEIGHT - FOOD_RADIUS * 5)
        food_center = (x + FOOD_RADIUS, y + FOOD_RADIUS)
        if point_in_polygon(food_center, pentagon_vertices):
            return (x, y)

def draw_food(surface, position, color):
    x, y = position
    pygame.draw.circle(surface, color, (x + FOOD_RADIUS, y + FOOD_RADIUS), FOOD_RADIUS)

# --------------------
# Score Setup (Increased Font Size)
# --------------------
score_font = pygame.font.SysFont("Arial", 36)  # Increased font size for score

def draw_score(surface, score, color):
    score_text = score_font.render(f"Score: {score}", True, color)
    surface.blit(score_text, (600, 600))

# --------------------
# Game Over Screen with "Play Again" Button
# --------------------
def game_over_screen():
    # Stop the background music.
    pygame.mixer.music.stop()
    # Create fonts for messages and button text.
    death_font = pygame.font.SysFont("Arial", 72)
    button_font = pygame.font.SysFont("Arial", 48)
    # Define the Play Again button rectangle.
    button_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 100, 200, 60)
    
    # Optionally, play the boring sound once at game over.
    boring_sound.play()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if button_rect.collidepoint(mouse_pos):
                    return  # Exit the game over screen and restart the game.
        
        win.fill(BLACK)
        draw_pentagon(win, pentagon_vertices, WHITE)
        
        # Display the death message.
        message = death_font.render("Oh No, you killed the snake", True, RED)
        message_rect = message.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        win.blit(message, message_rect)
        
        # Draw the Play Again button.
        pygame.draw.rect(win, BLUE, button_rect)
        button_text = button_font.render("Play Again", True, WHITE)
        button_text_rect = button_text.get_rect(center=button_rect.center)
        win.blit(button_text, button_text_rect)
        
        pygame.display.update()
        clock.tick(10)

# --------------------
# Game State Reset Function
# --------------------
def reset_game():
    global snake, score, direction, food_position, game_over
    # Initialize the snake at the center with an initial length.
    snake = [(WIDTH // 2, HEIGHT // 2)]
    initial_length = 3
    for i in range(1, initial_length):
        snake.append((WIDTH // 2 - i * SEGMENT_SIZE, HEIGHT // 2))
    score = 0
    direction = (SEGMENT_SIZE, 0)
    food_position = spawn_food()
    game_over = False
    # Restart background music.
    pygame.mixer.music.play(-1)

# --------------------
# Main Game Loop
# --------------------
# Set up initial game state.
reset_game()

running = True
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break  # Exit event loop
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and direction != (0, SEGMENT_SIZE):
                direction = (0, -SEGMENT_SIZE)
            elif event.key == pygame.K_DOWN and direction != (0, -SEGMENT_SIZE):
                direction = (0, SEGMENT_SIZE)
            elif event.key == pygame.K_LEFT and direction != (SEGMENT_SIZE, 0):
                direction = (-SEGMENT_SIZE, 0)
            elif event.key == pygame.K_RIGHT and direction != (-SEGMENT_SIZE, 0):
                direction = (SEGMENT_SIZE, 0)
    
    # Compute new head position.
    head_x, head_y = snake[0]
    dx, dy = direction
    new_head = (head_x + dx, head_y + dy)
    
    # Check collisions with self.
    if new_head in snake:
        print("Game Over! You collided with yourself.")
        game_over = True
    head_center = (new_head[0] + SEGMENT_SIZE // 2, new_head[1] + SEGMENT_SIZE // 2)
    # Check if the head is inside the pentagon.
    if not point_in_polygon(head_center, pentagon_vertices):
        print("Game Over! You hit the wall.")
        game_over = True

    if game_over:
        game_over_screen()  # Display death message and Play Again button.
        reset_game()        # Reinitialize the game state.
        continue  # Restart the game loop with the new state

    snake.insert(0, new_head)
    
    # Check for collision with food.
    food_rect = pygame.Rect(food_position[0], food_position[1], FOOD_RADIUS * 2, FOOD_RADIUS * 2)
    head_rect = pygame.Rect(new_head[0], new_head[1], SEGMENT_SIZE, SEGMENT_SIZE)
    if head_rect.colliderect(food_rect):
        score += 1
        food_position = spawn_food()
    else:
        snake.pop()

    win.fill(BLACK)
    draw_pentagon(win, pentagon_vertices, WHITE)
    draw_snake(win, snake, GREEN, TAIPAN_HEAD, direction)
    draw_food(win, food_position, RED)
    draw_score(win, score, YELLOW)
    
    pygame.display.update()

pygame.quit()
sys.exit()
