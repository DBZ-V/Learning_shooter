import pygame
import random
from ai_genocidax import GenocidaxAI
import torch

geno_ai = GenocidaxAI()
geno_memory = []  # memory for training

debug_mode = True
last_decision = ""

# Initialize pygame
pygame.init()

# Screen dimensions
width, height = 640, 480
cell_size = 20
cols, rows = width // cell_size, height // cell_size

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Genocidax Game")

clock = pygame.time.Clock()

# Font
font_path = "font/Perfect_DOS_VGA_437.ttf"

# Initialize sounds
pygame.mixer.init()
shoot_sound = pygame.mixer.Sound(pygame.mixer.Sound('sound/beep.wav'))
ennemy_shot = pygame.mixer.Sound(pygame.mixer.Sound('sound/pioupiou.wav'))
player_impact_sound = pygame.mixer.Sound(pygame.mixer.Sound('sound/kururi.wav'))
contact_sound = pygame.mixer.Sound(pygame.mixer.Sound("sound/tulut.wav"))
invincible_sound = pygame.mixer.Sound(pygame.mixer.Sound("sound/tiptip.wav"))

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
MAGENTA = (255, 0, 200)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)

# Screenshake
def screen_shake(offset_range=5, duration=300):
    shake_start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - shake_start < duration:
        offset_x = random.randint(-offset_range, offset_range)
        offset_y = random.randint(-offset_range, offset_range)
        screen.fill(BLACK)
        
        for y, x in obstacles:
            pygame.draw.rect(screen, MAGENTA, ((x * cell_size) + offset_x, (y * cell_size) + offset_y, cell_size, cell_size))
        for y, x in score_blocs:
            pygame.draw.rect(screen, BLUE, ((x * cell_size) + offset_x, (y * cell_size) + offset_y, cell_size, cell_size))
        pygame.draw.rect(screen, GREEN, (player_pos[0] * cell_size + offset_x, player_pos[1] * cell_size + offset_y, cell_size, cell_size))
        pygame.draw.rect(screen, RED, (geno_pos[0] * cell_size + offset_x, geno_pos[1] * cell_size + offset_y, cell_size, cell_size))

        pygame.display.flip()
        pygame.time.delay(30)



# Statut
invincible = False
invincible_timer = 0


# Obstacles
obstacles = set()
for _ in range(40):
    obstacles.add((random.randint(3, rows - 4), random.randint(0, cols - 1)))

# Score Bloc for the HUD
score_blocs = set()
for y in range(2):  # first 2 lines
    for x in range(cols):
        score_blocs.add((y, x))

player_direction = [0, -1]
geno_direction = [0, 1]


# Game entities
player_pos = [cols // 2, rows - 2]

while True:
    gx, gy = random.randint(0, cols - 1), random.randint(2, rows // 2)
    if (gy, gx) not in obstacles and (gy, gx) not in score_blocs:
        geno_pos = [gx, gy]
        break

player_bullet = None
geno_bullet = None
player_score, geno_score, player_shots, geno_shots = 0, 0, 0, 0



# Game loop
running = True
geno_move_counter = 0
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            new_pos = player_pos[:]
            if event.key == pygame.K_LEFT:
                new_pos[0] -= 1
                player_direction = [-1, 0]
            elif event.key == pygame.K_RIGHT:
                new_pos[0] += 1
                player_direction = [1, 0]
            elif event.key == pygame.K_UP:
                new_pos[1] -= 1
                player_direction = [0, -1]
            elif event.key == pygame.K_DOWN:
                new_pos[1] += 1
                player_direction = [0, 1]
            elif event.key == pygame.K_SPACE and player_bullet is None:
                player_bullet = [player_pos[0] + player_direction[0], player_pos[1] + player_direction[1], player_direction[:]]
                shoot_sound.play()
                player_shots += 1
            elif event.key == pygame.K_i:
                # manual invicible
                invincible = True
                invincible_timer = pygame.time.get_ticks()
                print("You're on a sugar rush !")
            if 0 <= new_pos[0] < cols and 0 <= new_pos[1] < rows and (new_pos[1], new_pos[0]) not in obstacles and (new_pos[1], new_pos[0]) not in score_blocs:
                player_pos = new_pos
            if invincible:
                if pygame.time.get_ticks() - invincible_timer >= 3000:  # 3 sec
                    invincible = False

                

    # Move player bullet
    if player_bullet:
        player_bullet[0] += player_bullet[2][0]
        player_bullet[1] += player_bullet[2][1]
        if (player_bullet[1], player_bullet[0]) in obstacles or player_bullet[1] < 0 or player_bullet[1] >= rows or player_bullet[0] < 0 or player_bullet[0] >= cols:
            player_bullet = None
        elif [player_bullet[0], player_bullet[1]] == geno_pos:
            player_score += 1
            # Puniting last action
            if geno_memory:
                s, a, _ = geno_memory[-1]
                # Distance before shot
                dx = player_bullet[0] - player_pos[0]
                dy = player_bullet[1] - player_pos[1]
                distance = (dx**2 + dy**2) ** 0.5
                penalty = -3.0 * distance

                geno_memory[-1] = (s, a, penalty)
            geno_ai.save_model() 
            player_impact_sound.play()
            
            # Blinking
            for _ in range(3):
                pygame.draw.rect(screen, YELLOW, (geno_pos[0] * cell_size, geno_pos[1] * cell_size, cell_size, cell_size))
                pygame.display.flip()
                pygame.time.delay(50)
                pygame.draw.rect(screen, BLACK, (geno_pos[0] * cell_size, geno_pos[1] * cell_size, cell_size, cell_size))
                pygame.display.flip()
                pygame.time.delay(50)

            # Repawn random (avoid obstacle + HUD)
            while True:
                gx, gy = random.randint(0, cols - 1), random.randint(2, rows // 2)
                if (gy, gx) not in obstacles and (gy, gx) not in score_blocs:
                    geno_pos = [gx, gy]
                    break            
            player_bullet = None

    # Slow down Genocidax
    geno_move_counter += 1
    if geno_move_counter % 1 == 0:
        # Actual state
        state_tensor = geno_ai.build_state_tensor(player_pos, geno_pos, player_bullet, geno_bullet, obstacles)


        # Décision AI
        decision = geno_ai.decide_action(player_pos, geno_pos, player_bullet, geno_bullet, obstacles)
        if debug_mode:
            last_decision = decision

        action_map = {"UP": 0, "DOWN": 1, "LEFT": 2, "RIGHT": 3, "SHOOT": 4}
        geno_memory.append((state_tensor, action_map[decision], 0.0))  # reward 0 par défaut


        # Line learning ligne
        geno_ai.train(geno_memory)

        # Apply decision
        if decision in ["UP", "DOWN", "LEFT", "RIGHT"]:
            move_dict = {
                "UP": [0, -1],
                "DOWN": [0, 1],
                "LEFT": [-1, 0],
                "RIGHT": [1, 0]
            }
            geno_direction = move_dict[decision]
            new_geno_pos = [geno_pos[0] + geno_direction[0], geno_pos[1] + geno_direction[1]]
            if 0 <= new_geno_pos[0] < cols and 0 <= new_geno_pos[1] < rows//2 and (new_geno_pos[1], new_geno_pos[0]) not in obstacles and (new_geno_pos[1], new_geno_pos[0]) not in score_blocs:
                geno_pos = new_geno_pos

        elif decision == "SHOOT" and geno_bullet is None:
            geno_bullet = [geno_pos[0] + geno_direction[0], geno_pos[1] + geno_direction[1], geno_direction[:]]
            ennemy_shot.play()
            geno_shots += 1

            # Low reward in cas of shoot (even if no hit)
            if geno_memory:
                s, a, _ = geno_memory[-1]
                geno_memory[-1] = (s, a, 0.5)


    # Move genocidax bullet
    if geno_bullet:
        geno_bullet[0] += geno_bullet[2][0]
        geno_bullet[1] += geno_bullet[2][1]
        if (geno_bullet[1], geno_bullet[0]) in obstacles or geno_bullet[1] < 0 or geno_bullet[1] >= rows or geno_bullet[0] < 0 or geno_bullet[0] >= cols:
            geno_bullet = None
        elif [geno_bullet[0], geno_bullet[1]] == player_pos and not invincible:
            geno_score += 1
            geno_ai.save_model()
            invincible_sound.play()
            # Update reward in buffer
            if geno_memory:
                s, a, _ = geno_memory[-1]
                geno_memory[-1] = (s, a, 3.0)  # Positive reward after kill
            contact_sound.play()
            screen_shake()

            # Flashing
            for _ in range(3):
                pygame.draw.rect(screen, YELLOW, (player_pos[0] * cell_size, player_pos[1] * cell_size, cell_size, cell_size))
                pygame.display.flip()
                pygame.time.delay(80)
                pygame.draw.rect(screen, BLACK, (player_pos[0] * cell_size, player_pos[1] * cell_size, cell_size, cell_size))
                pygame.display.flip()
                pygame.time.delay(80)

            
            while True:
                px, py = random.randint(0, cols - 1), random.randint(2, rows - 1)
                if (py, px) not in obstacles and (py, px) not in score_blocs:
                    player_pos = [px, py]
                    break

            # Activate invicible
            invincible = True
            invincible_timer = pygame.time.get_ticks()
            
            geno_bullet = None



    # Contact
    if player_pos == geno_pos and not invincible:
        contact_sound.play()
        geno_score += 1
        geno_ai.save_model()
        invincible_sound.play()
        # Update reward in buffer
        if geno_memory:
            s, a, _ = geno_memory[-1]
            geno_memory[-1] = (s, a, 100.0)  # Positive reward after kill
        screen_shake()

        # Flashing
        for _ in range(3):
            pygame.draw.rect(screen, YELLOW, (player_pos[0] * cell_size, player_pos[1] * cell_size, cell_size, cell_size))
            pygame.display.flip()
            pygame.time.delay(80)
            pygame.draw.rect(screen, BLACK, (player_pos[0] * cell_size, player_pos[1] * cell_size, cell_size, cell_size))
            pygame.display.flip()
            pygame.time.delay(80)

        while True:
            px, py = random.randint(0, cols - 1), random.randint(2, rows - 1)
            if (py, px) not in obstacles and (py, px) not in score_blocs:
                player_pos = [px, py]
                invincible = True
                invincible_timer = pygame.time.get_ticks()
                break

    # Draw everything
    screen.fill(BLACK)

    # Display invicibility barre
    if invincible:
        time_left = max(0, 3000 - (pygame.time.get_ticks() - invincible_timer))  # 3 sec
        bar_width = int((time_left / 3000) * width)
        pygame.draw.rect(screen, YELLOW, (0, height - 10, width, 10))       # YELLOW background
        pygame.draw.rect(screen, CYAN, (0, height - 10, bar_width, 10))    # CYAN barre




    for y, x in obstacles:
        pygame.draw.rect(screen, MAGENTA, (x * cell_size, y * cell_size, cell_size, cell_size))

    pygame.draw.rect(screen, GREEN, (player_pos[0] * cell_size, player_pos[1] * cell_size, cell_size, cell_size))
    pygame.draw.rect(screen, RED, (geno_pos[0] * cell_size, geno_pos[1] * cell_size, cell_size, cell_size))

    if player_bullet:
        pygame.draw.rect(screen, GREEN, (player_bullet[0] * cell_size + cell_size//4, player_bullet[1] * cell_size + cell_size//4, cell_size//2, cell_size//2))
    if geno_bullet:
        pygame.draw.rect(screen, RED, (geno_bullet[0] * cell_size + cell_size//4, geno_bullet[1] * cell_size + cell_size//4, cell_size//2, cell_size//2))

    for y, x in score_blocs:
        pygame.draw.rect(screen, BLUE, (x * cell_size, y * cell_size, cell_size, cell_size))

  
    # Safe division (avoid /0)
    player_accuracy = (player_score * 100 // player_shots) if player_shots > 0 else 0
    geno_accuracy = (geno_score * 100 // geno_shots) if geno_shots > 0 else 0

  
    # Display scores
    font = pygame.font.Font(font_path, 20)
    # score_text = font.render(f'GENOCIDAX: {geno_score:03d}   YOU: {player_score:03d}', True, WHITE)
    score_text = font.render(
    f'GENOCIDAX: {geno_score:03d} ({geno_shots}, {geno_accuracy}%)   YOU: {player_score:03d} ({player_shots}, {player_accuracy}%)',
    True, WHITE
    )
    screen.blit(score_text, (10, 10))

    if debug_mode:
        debug_font = pygame.font.Font(font_path, 14)
        debug_text = debug_font.render(f"IA: {last_decision}", True, CYAN)
        screen.blit(debug_text, (10, height - 30))

    pygame.display.flip()
    clock.tick(20)

pygame.quit()