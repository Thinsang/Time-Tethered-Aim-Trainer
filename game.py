import pygame
import sys
import random
import time
import math
import json
import os
from collections import deque

# Initialize pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
GREY = (180, 180, 180)

# Game settings
GAME_DURATION = 30  # seconds
TRACER_LENGTH = 20  # Number of previous mouse positions to store
TRACER_FADE = 200  # How quickly tracers fade (higher = slower fade)

# Difficulty presets
DIFFICULTY_SETTINGS = {
    "Easy": {
        "target_size": 40,
        "spawn_rate": 1.5,
        "max_targets": 4
    },
    "Medium": {
        "target_size": 30,
        "spawn_rate": 1.0,
        "max_targets": 6
    },
    "Hard": {
        "target_size": 20,
        "spawn_rate": 0.7,
        "max_targets": 8
    }
}

# Leaderboard file
LEADERBOARD_FILE = "aim_trainer_leaderboard.json"

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.current_color = color
        self.text_color = BLACK
        self.font = pygame.font.SysFont(None, 36)
        
    def draw(self, surface):
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=10)
        pygame.draw.rect(surface, BLACK, self.rect, 2, border_radius=10)
        
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def update(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
        else:
            self.current_color = self.color
            
    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

class Target:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.radius = size // 2
        self.spawn_time = time.time()
        self.color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        self.is_hit = False
        self.hit_time = 0
        self.hit_animation_duration = 0.3  # seconds
        
    def draw(self, surface):
        if self.is_hit:
            # Animation for hit targets
            animation_progress = min(1.0, (time.time() - self.hit_time) / self.hit_animation_duration)
            
            # Shrink and fade out
            current_radius = int(self.radius * (1 - animation_progress))
            fade_color = [c * (1 - animation_progress) for c in self.color]
            
            # Draw explosion effect
            for i in range(8):
                angle = i * math.pi / 4
                distance = self.radius * animation_progress * 2
                end_x = self.x + math.cos(angle) * distance
                end_y = self.y + math.sin(angle) * distance
                
                # Sparkle line
                pygame.draw.line(surface, self.color, 
                                (self.x, self.y), 
                                (end_x, end_y), 
                                max(1, int(3 * (1 - animation_progress))))
            
            # Draw shrinking circle
            if current_radius > 0:
                pygame.draw.circle(surface, fade_color, (self.x, self.y), current_radius)
        else:
            pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius)
            pygame.draw.circle(surface, BLACK, (self.x, self.y), self.radius, 2)
        
    def is_clicked(self, pos):
        dx = self.x - pos[0]
        dy = self.y - pos[1]
        return (dx * dx + dy * dy) <= (self.radius * self.radius)
    
    def hit(self):
        self.is_hit = True
        self.hit_time = time.time()
        
    def is_animation_finished(self):
        if not self.is_hit:
            return False
        return (time.time() - self.hit_time) >= self.hit_animation_duration

class Leaderboard:
    def __init__(self):
        self.scores = {"Easy": [], "Medium": [], "Hard": []}
        self.load()
        
    def load(self):
        try:
            if os.path.exists(LEADERBOARD_FILE):
                with open(LEADERBOARD_FILE, 'r') as f:
                    self.scores = json.load(f)
        except Exception as e:
            print(f"Error loading leaderboard: {e}")
            self.scores = {"Easy": [], "Medium": [], "Hard": []}
            
    def save(self):
        try:
            with open(LEADERBOARD_FILE, 'w') as f:
                json.dump(self.scores, f)
        except Exception as e:
            print(f"Error saving leaderboard: {e}")
            
    def add_score(self, difficulty, score):
        if difficulty not in self.scores:
            self.scores[difficulty] = []
            
        self.scores[difficulty].append(score)
        # Sort scores in descending order
        self.scores[difficulty].sort(reverse=True)
        # Keep only top 10 scores
        self.scores[difficulty] = self.scores[difficulty][:10]
        self.save()
        
    def get_top_scores(self, difficulty, count=5):
        if difficulty not in self.scores:
            return []
        
        return self.scores[difficulty][:count]
        
    def get_rank(self, difficulty, score):
        if difficulty not in self.scores:
            return 1
            
        # Count how many scores are higher than this one
        rank = 1
        for s in self.scores[difficulty]:
            if s > score:
                rank += 1
        return rank

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Time Tethered: Aim Trainer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.title_font = pygame.font.SysFont(None, 60)
        self.subtitle_font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)
        
        # Leaderboard
        self.leaderboard = Leaderboard()
        
        # Game states
        self.state = "home"  # "home", "game", "game_over", "leaderboard"
        self.difficulty = "Medium"  # Default difficulty
        
        # Initialize buttons
        self.setup_home_screen()
        self.reset_game()
        
    def setup_home_screen(self):
        center_x = WIDTH // 2
        
        # Play button (larger)
        play_button_width = 200
        play_button_height = 60
        play_y = HEIGHT // 2 - 30
        self.play_button = Button(
            center_x - play_button_width // 2, 
            play_y,
            play_button_width, 
            play_button_height,
            "PLAY", 
            ORANGE,
            (255, 200, 100)
        )
        
        # Leaderboard button
        leaderboard_button_width = 200
        leaderboard_button_height = 40
        leaderboard_y = HEIGHT // 2 + 50
        self.leaderboard_button = Button(
            center_x - leaderboard_button_width // 2,
            leaderboard_y,
            leaderboard_button_width,
            leaderboard_button_height,
            "LEADERBOARD",
            (100, 200, 255),
            (150, 220, 255)
        )
        
        # Difficulty buttons (smaller and horizontal)
        diff_button_width = 120
        diff_button_height = 40
        diff_y = HEIGHT // 2 + 120
        
        self.difficulty_buttons = []
        difficulties = ["Easy", "Medium", "Hard"]
        
        # Calculate spacing to center the three buttons
        total_width = diff_button_width * 3 + 20 * 2  # 3 buttons with 20px spacing between
        start_x = center_x - total_width // 2
        
        for i, diff in enumerate(difficulties):
            is_selected = diff == self.difficulty
            diff_button = Button(
                start_x + i * (diff_button_width + 20),
                diff_y,
                diff_button_width,
                diff_button_height,
                diff,
                PURPLE if is_selected else GREY,  # Selected is purple, non-selected is grey
                PURPLE  # Hover color is always purple
            )
            self.difficulty_buttons.append(diff_button)
        
    def reset_game(self):
        # Apply difficulty settings
        settings = DIFFICULTY_SETTINGS[self.difficulty]
        self.target_size = settings["target_size"]
        self.spawn_rate = settings["spawn_rate"]
        self.max_targets = settings["max_targets"]
        
        # Reset game state
        self.score = 0
        self.targets = []
        self.last_spawn_time = time.time()
        self.game_start_time = time.time()
        self.mouse_positions = deque(maxlen=TRACER_LENGTH)
        
    def spawn_target(self):
        if len([t for t in self.targets if not t.is_hit]) < self.max_targets:
            # Ensure targets don't spawn too close to the edge
            margin = self.target_size
            x = random.randint(margin, WIDTH - margin)
            y = random.randint(margin, HEIGHT - margin)
            
            # Check that the new target isn't too close to existing targets
            valid_position = True
            for target in self.targets:
                if target.is_hit:
                    continue
                dx = target.x - x
                dy = target.y - y
                distance = (dx * dx + dy * dy) ** 0.5
                if distance < self.target_size * 2:
                    valid_position = False
                    break
                    
            if valid_position:
                self.targets.append(Target(x, y, self.target_size))
            
    def update(self):
        if self.state == "home" or self.state == "leaderboard":
            mouse_pos = pygame.mouse.get_pos()
            self.play_button.update(mouse_pos)
            self.leaderboard_button.update(mouse_pos)
            for button in self.difficulty_buttons:
                button.update(mouse_pos)
                
        elif self.state == "game":
            current_time = time.time()
            remaining_time = max(0, GAME_DURATION - (current_time - self.game_start_time))
            
            # Game over condition
            if remaining_time <= 0:
                self.state = "game_over"
                # Add score to leaderboard
                self.leaderboard.add_score(self.difficulty, self.score)
                
            # Spawn new targets
            if current_time - self.last_spawn_time > self.spawn_rate:
                self.spawn_target()
                self.last_spawn_time = current_time
                
            # Store current mouse position for tracers
            self.mouse_positions.append(pygame.mouse.get_pos())
            
            # Remove finished hit animations
            self.targets = [t for t in self.targets if not t.is_animation_finished()]
            
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "game" or self.state == "game_over" or self.state == "leaderboard":
                        self.state = "home"
                        self.setup_home_screen()
                    else:
                        pygame.quit()
                        sys.exit()
                        
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "home":
                    if self.play_button.is_clicked(event.pos):
                        self.state = "game"
                        self.reset_game()
                    
                    if self.leaderboard_button.is_clicked(event.pos):
                        self.state = "leaderboard"
                    
                    for i, button in enumerate(self.difficulty_buttons):
                        if button.is_clicked(event.pos):
                            self.difficulty = ["Easy", "Medium", "Hard"][i]
                            # Update button colors when selection changes
                            self.setup_home_screen()
                
                elif self.state == "game":
                    hit = False
                    for target in self.targets:
                        if not target.is_hit and target.is_clicked(event.pos):
                            target.hit()
                            self.score += 1
                            hit = True
                            break
                    
                    if not hit:  # Penalty for missing
                        self.score = max(0, self.score - 1)
                
                elif self.state == "game_over" or self.state == "leaderboard":
                    self.state = "home"
                    self.setup_home_screen()
    
    def draw_home_screen(self):
        self.screen.fill(WHITE)
        
        # Draw title
        title_text = self.title_font.render("Time Tethered: Aim Trainer", True, BLACK)
        title_rect = title_text.get_rect(center=(WIDTH//2, HEIGHT//4))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle with current difficulty
        subtitle_text = self.subtitle_font.render(f"Current Difficulty: {self.difficulty}", True, PURPLE)
        subtitle_rect = subtitle_text.get_rect(center=(WIDTH//2, HEIGHT//4 + 50))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Draw buttons
        self.play_button.draw(self.screen)
        self.leaderboard_button.draw(self.screen)
        for button in self.difficulty_buttons:
            button.draw(self.screen)
            
    def draw_leaderboard(self):
        self.screen.fill(WHITE)
        
        # Draw title
        title_text = self.title_font.render("Leaderboard", True, BLACK)
        title_rect = title_text.get_rect(center=(WIDTH//2, 60))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle
        subtitle_text = self.font.render(f"Difficulty: {self.difficulty}", True, PURPLE)
        subtitle_rect = subtitle_text.get_rect(center=(WIDTH//2, 110))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Draw top scores
        top_scores = self.leaderboard.get_top_scores(self.difficulty)
        
        if not top_scores:
            no_scores_text = self.font.render("No scores yet!", True, BLACK)
            no_scores_rect = no_scores_text.get_rect(center=(WIDTH//2, HEIGHT//2))
            self.screen.blit(no_scores_text, no_scores_rect)
        else:
            # Draw header
            header_y = 160
            pygame.draw.line(self.screen, BLACK, (WIDTH//4, header_y), (WIDTH*3//4, header_y), 2)
            
            rank_text = self.font.render("Rank", True, BLACK)
            self.screen.blit(rank_text, (WIDTH//4, header_y + 10))
            
            score_text = self.font.render("Score", True, BLACK)
            score_rect = score_text.get_rect(midright=(WIDTH*3//4, header_y + 30))
            self.screen.blit(score_text, score_rect)
            
            pygame.draw.line(self.screen, BLACK, (WIDTH//4, header_y + 50), (WIDTH*3//4, header_y + 50), 2)
            
            # Draw scores
            for i, score in enumerate(top_scores):
                y_pos = header_y + 70 + i * 50
                
                # Rank
                rank_text = self.font.render(f"{i+1}.", True, BLACK)
                self.screen.blit(rank_text, (WIDTH//4, y_pos))
                
                # Score
                score_text = self.font.render(f"{score}", True, BLACK)
                score_rect = score_text.get_rect(midright=(WIDTH*3//4, y_pos + 20))
                self.screen.blit(score_text, score_rect)
        
        # Back button instruction
        back_text = self.small_font.render("Press ESC or click anywhere to return to menu", True, BLACK)
        back_rect = back_text.get_rect(center=(WIDTH//2, HEIGHT - 40))
        self.screen.blit(back_text, back_rect)
            
    def draw_game(self):
        self.screen.fill(WHITE)
        
        # Draw tethered mouse trail
        for i, pos in enumerate(self.mouse_positions):
            # Calculate opacity based on position in the queue
            # Newer positions are more opaque
            opacity = min(255, int((i / TRACER_LENGTH) * TRACER_FADE))
            color = (0, opacity, 255)
            size = max(3, int((i / TRACER_LENGTH) * 10))
            pygame.draw.circle(self.screen, color, pos, size)
        
        # Draw targets
        for target in self.targets:
            target.draw(self.screen)
            
        # Draw current mouse position with a crosshair
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.line(self.screen, BLACK, (mouse_pos[0] - 10, mouse_pos[1]), (mouse_pos[0] + 10, mouse_pos[1]), 2)
        pygame.draw.line(self.screen, BLACK, (mouse_pos[0], mouse_pos[1] - 10), (mouse_pos[0], mouse_pos[1] + 10), 2)
        
        # Draw UI
        current_time = time.time()
        remaining_time = max(0, GAME_DURATION - (current_time - self.game_start_time))
        time_text = self.font.render(f"Time: {int(remaining_time)}", True, BLACK)  # Integer time display
        score_text = self.font.render(f"Score: {self.score}", True, BLACK)
        
        self.screen.blit(time_text, (10, 10))
        self.screen.blit(score_text, (10, 50))
        
    def draw_game_over(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        # Game over text
        game_over_text = self.title_font.render("GAME OVER", True, RED)
        restart_text = self.font.render("Click anywhere to return to menu", True, WHITE)
        final_score_text = self.font.render(f"Final Score: {self.score}", True, YELLOW)
        
        # Get rank info
        rank = self.leaderboard.get_rank(self.difficulty, self.score)
        rank_text = self.font.render(f"Rank: #{rank} in {self.difficulty} mode", True, CYAN)
        
        # Position all text
        text_rect = game_over_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 80))
        self.screen.blit(game_over_text, text_rect)
        
        text_rect = final_score_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 20))
        self.screen.blit(final_score_text, text_rect)
        
        text_rect = rank_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 20))
        self.screen.blit(rank_text, text_rect)
        
        text_rect = restart_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 80))
        self.screen.blit(restart_text, text_rect)
    
    def draw(self):
        if self.state == "home":
            self.draw_home_screen()
        elif self.state == "game":
            self.draw_game()
        elif self.state == "game_over":
            self.draw_game()  # Draw the game state in background
            self.draw_game_over()  # Overlay game over screen
        elif self.state == "leaderboard":
            self.draw_leaderboard()
        
        pygame.display.flip()
    
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()