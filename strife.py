import pygame
import sys
import math
import random
import time

import strifelib

# Constants for visualization
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
FPS = 60
BACKGROUND_COLOR = (20, 20, 20)
MARGIN = 30  # Margin size around the arena (size of one bot)
BOT_COLORS = [
	(255, 100, 100),  # Red
	(100, 100, 255),  # Blue
	(100, 255, 100),  # Green
	(255, 255, 100),  # Yellow
	(255, 100, 255),  # Magenta
	(100, 255, 255),  # Cyan
	(255, 165, 0),    # Orange
	(128, 0, 128)     # Purple
]
BULLET_RADIUS = 3


class Visualizer:
	def __init__(self, arena_size):
		pygame.init()
		self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
		pygame.display.set_caption("RoboBot Battle Arena")
		self.clock = pygame.time.Clock()
		self.font = pygame.font.SysFont("monospace", 14)
		self.arena_size = arena_size

		# Calculate scale with margin
		self.display_width = SCREEN_WIDTH - (2 * MARGIN)
		self.display_height = SCREEN_HEIGHT - (2 * MARGIN)
		self.scale_x = self.display_width / arena_size[0]
		self.scale_y = self.display_height / arena_size[1]

		self.bot_colors = {}
		self.running = True
		self.paused = False
		self.speed = 1  # Ticks per frame

	def handle_events(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.running = False
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					self.running = False
				elif event.key == pygame.K_SPACE:
					self.paused = not self.paused
				elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
					self.speed = min(10, self.speed + 1)
				elif event.key == pygame.K_MINUS:
					self.speed = max(1, self.speed - 1)

	def draw_arena(self):
		# Draw background
		self.screen.fill(BACKGROUND_COLOR)

		# Draw arena area with margin
		pygame.draw.rect(self.screen, (40, 40, 40),
						 (MARGIN, MARGIN, self.display_width, self.display_height))

		# Draw border
		pygame.draw.rect(self.screen, (100, 100, 100),
						 (MARGIN, MARGIN, self.display_width, self.display_height), 2)

	def draw_bot(self, bot, bot_index):
		# Assign a color to this bot if not already assigned
		if bot not in self.bot_colors:
			self.bot_colors[bot] = BOT_COLORS[bot_index % len(BOT_COLORS)]

		color = self.bot_colors[bot]

		# Convert arena coordinates to screen coordinates with margin
		x = int(bot.position[0] * self.scale_x) + MARGIN
		y = int(bot.position[1] * self.scale_y) + MARGIN

		# Draw bot body
		pygame.draw.circle(self.screen, color, (x, y), bot.radius)

		# Draw tracks direction indicator
		tracks_rad = math.radians((bot.tracks_direction - 90) % 360)
		tracks_x = x + int(bot.radius * 1.5 * math.cos(tracks_rad))
		tracks_y = y + int(bot.radius * 1.5 * math.sin(tracks_rad))
		pygame.draw.line(self.screen, (200, 200, 200), (x, y), (tracks_x, tracks_y), 2)

		# Draw aim direction indicator
		aim_rad = math.radians((bot.aim_direction - 90) % 360)
		aim_x = x + int(bot.radius * 2 * math.cos(aim_rad))
		aim_y = y + int(bot.radius * 2 * math.sin(aim_rad))
		pygame.draw.line(self.screen, (255, 0, 0), (x, y), (aim_x, aim_y), 2)

		# Draw health bar
		health_width = int(bot.radius * 2 * (bot.health / 100))
		pygame.draw.rect(self.screen, (50, 50, 50),
						 (x - bot.radius, y - bot.radius - 8, bot.radius * 2, 5))
		pygame.draw.rect(self.screen, (0, 255, 0),
						 (x - bot.radius, y - bot.radius - 8, health_width, 5))

		# Draw energy bar
		energy_width = int(bot.radius * 2 * (bot.energy / 100))
		pygame.draw.rect(self.screen, (50, 50, 50),
						 (x - bot.radius, y - bot.radius - 14, bot.radius * 2, 5))
		pygame.draw.rect(self.screen, (0, 100, 255),
						 (x - bot.radius, y - bot.radius - 14, energy_width, 5))

		# Draw bot name
		name_text = self.font.render(bot.name, True, (200, 200, 200))
		self.screen.blit(name_text, (x - name_text.get_width() // 2, y + bot.radius + 5))

	def draw_bullet(self, bullet):
		# Convert arena coordinates to screen coordinates with margin
		x = int(bullet.position[0] * self.scale_x) + MARGIN
		y = int(bullet.position[1] * self.scale_y) + MARGIN

		# Draw bullet with color based on power
		color_intensity = min(255, bullet.power * 25)
		color = (color_intensity, color_intensity, 255 - color_intensity)

		pygame.draw.circle(self.screen, color, (x, y), BULLET_RADIUS)

	def draw_info(self, arena):
		# Draw tick count
		tick_text = self.font.render(f"Tick: {arena.tick_count}", True, (200, 200, 200))
		self.screen.blit(tick_text, (10, 10))

		# Draw speed indicator
		speed_text = self.font.render(f"Speed: {self.speed}x", True, (200, 200, 200))
		self.screen.blit(speed_text, (10, 30))

		# Draw pause indicator if paused
		if self.paused:
			pause_text = self.font.render("PAUSED", True, (255, 100, 100))
			self.screen.blit(pause_text, (10, 50))

		# Draw number of bots and bullets
		stats_text = self.font.render(
			f"Bots: {len(arena.bots)}  Bullets: {len(arena.bullets)}",
			True, (200, 200, 200)
		)
		self.screen.blit(stats_text, (10, 70))

	def draw(self, arena):
		self.draw_arena()

		# Draw all bullets
		for bullet in arena.bullets:
			self.draw_bullet(bullet)

		# Draw all bots
		for i, bot in enumerate(arena.bots):
			self.draw_bot(bot, i)

		# self.draw_info(arena)

		# Update display
		pygame.display.flip()
		self.clock.tick(FPS)

	def close(self):
		pygame.quit()


def main():
	arena = strifelib.Arena()

	# Load bot programs from command line arguments
	for filename in sys.argv[1:]:
		with open(filename, encoding="utf-8") as infile:
			code = infile.read()
			arena.add_bot(code, filename)

	# Assuming bot files will be passed as arguments
	if len(arena.bots) == 0:
		print("No bot files specified. Please provide bot files as arguments.")
		return

	# Create visualizer
	visualizer = Visualizer(arena.size)

	# Run simulation
	max_ticks = 2000
	tick = 0

	while tick < max_ticks and not arena.is_battle_over() and visualizer.running:
		visualizer.handle_events()

		if not visualizer.paused:
			# Run multiple ticks per frame based on speed setting
			for _ in range(visualizer.speed):
				arena.tick()
				tick += 1

				if arena.is_battle_over():
					break

		visualizer.draw(arena)

	# Keep window open to display final state
	end_time = time.time() + 3  # Show final state for 3 seconds
	while visualizer.running and time.time() < end_time:
		visualizer.handle_events()
		visualizer.draw(arena)

	# Report results
	winner = arena.get_winner()
	if winner:
		print(f"Battle over after {arena.tick_count} ticks")
		print(f"Winner: {winner.name} with {winner.health:.1f} health remaining")
	else:
		print(f"Battle ended in a draw after {arena.tick_count} ticks")

	visualizer.close()


if __name__ == "__main__":
	main()