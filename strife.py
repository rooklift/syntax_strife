import math
import random
import sys

MAX_HEALTH = 100
MAX_ENERGY = 100
BOT_RADIUS = 20

class RoboBot:
	def __init__(self, program, name="Bot"):
		self.name = name
		self.program = program
		self.tokens, self.token_counts = self.tokenize(program)
		self.position = (0, 0)		# To be set from outside
		self.health = MAX_HEALTH
		self.energy = MAX_ENERGY
		self.tracks_direction = 0	# 0-359 degrees
		self.aim_direction = 0		# 0-359 degrees
		self.speed = 0				# 0-10 units per tick

		# Execution state
		self.pc = 0					# Program counter
		self.stack = []				# Data stack
		self.variables = {}			# Named variables
		self.labels = self.find_labels()

		# Limits
		self.ops_per_tick = 50
		self.ops_executed = 0

	def tokenize(self, program):

		lines = program.split("\n")
		tokens = []
		counts = []

		for line in lines:

			if "#" in line:
				line = line[:line.index("#")]				# Remove comments

			line = line.strip()

			if not line:
				line_tokens = []							# No tokens on this line
			elif ":" in line:								# Line with a label
				label_part = line.split(":", 1)[0].strip()
				rest_part = line.split(":", 1)[1].strip()
				line_tokens = []
				line_tokens.append(f"{label_part}:")		# Add label as a token with colon
				if rest_part:
					line_tokens.extend(rest_part.split())
			else:											# Normal line
				line_tokens = line.split()

			tokens.extend(line_tokens)
			counts.append(len(line_tokens))

		return tokens, counts

	def find_labels(self):
		"""Find all label definitions in the program"""
		labels = {}
		for i, token in enumerate(self.tokens):
			if token.endswith(":"):
				# Remove colon from label name
				label_name = token[:-1]
				# Remove quotes if present (for consistent lookup)
				if label_name.startswith('"') and label_name.endswith('"'):
					label_name = label_name[1:-1]
				labels[label_name] = i + 1  # Point to instruction after label
		return labels

	def tick(self, arena):
		try:
			if self.health <= 0:
				return
			self.energy += 5
			if self.energy < 0:
				return
			if self.energy > MAX_ENERGY:
				self.energy = MAX_ENERGY
			self.move(arena)
			self.ops_executed = 0			# Reset for this tick
			while self.ops_executed < self.ops_per_tick:
				if self.energy < 0:
					return
				self.execute_next(arena)

		except Exception as e:

			print("\n", self.name, e)

			n = 0
			for i, c in enumerate(self.token_counts):
				n += c
				if n >= self.pc:
					print(f"Line {i}:  ", self.program.split("\n")[i], "\n")
					break

			self.health = 0
			return

	def move(self, arena):

		# Convert direction to radians for trig functions
		# Modified to make 0 degrees point up

		if self.speed > 0:
			rad = math.radians((self.tracks_direction - 90) % 360)
			dx = math.cos(rad) * self.speed
			dy = math.sin(rad) * self.speed

			x, y = self.position
			new_x = x + dx
			new_y = y + dy

			# Simple boundary check
			new_x = max(0, min(arena.size[0], new_x))
			new_y = max(0, min(arena.size[1], new_y))

			self.position = (new_x, new_y)

	def get_address_from_item(self, stack_item):
		if isinstance(stack_item, int):
			return stack_item
		return self.labels[stack_item]

	def execute_next(self, arena):

		if len(self.stack) > 100:
			raise MemoryError("Stack overflow")

		token = self.tokens[self.pc]
		self.pc += 1					# So self.pc now points to the token after this one. CALL can thus use it as is.

		# Count this operation
		self.ops_executed += 1

		if token.endswith(":") and token[:-1] in self.labels:
			return						# It's a label so it does nothing itself.

		# STATUS : place basic info on the stack

		elif token == "X":
			self.stack.append(int(self.position[0]))

		elif token == "Y":
			self.stack.append(int(self.position[1]))

		elif token == "TRACKS":
			self.stack.append(self.tracks_direction)

		elif token == "AIM":
			self.stack.append(self.aim_direction)

		elif token == "SPEED":
			self.stack.append(self.speed)

		elif token == "HEALTH":
			self.stack.append(self.health)

		elif token == "ENERGY":
			self.stack.append(self.energy)

		elif token == "SCAN":
			distance = self.scan_for_enemies(arena)
			self.stack.append(distance)

		# BOT ADJUSTMENTS : consume energy to do things

		elif token == "SETTRACKS":
			new_direction = int(self.stack.pop()) % 360
			energy_cost = calculate_direction_change_cost(self.tracks_direction, new_direction)
			self.energy -= energy_cost
			self.tracks_direction = new_direction

		elif token == "SETAIM":
			new_direction = int(self.stack.pop()) % 360
			self.energy -= 2  # Fixed cost
			self.aim_direction = new_direction

		elif token == "SETSPEED":
			new_speed = min(10, max(0, int(self.stack.pop())))
			self.energy -= new_speed  # Cost equals new speed
			self.speed = new_speed

		elif token == "FIRE":
			power = min(10, max(1, int(self.stack.pop())))
			self.energy -= 2 * power  # Cost is 2 * power
			self.fire_weapon(power, arena)

		# DUP : duplicate top stack item

		elif token == "DUP":
			self.stack.append(self.stack[-1])

		# DROP : pop item without using it

		elif token == "DROP":
			self.stack.pop()

		# SWAP : swap top 2 items on stack

		elif token == "SWAP":
			self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

		# IFELSE : if stack[-3] then put stack[-2] on top, else put stack[-1] on top

		elif token == "IFELSE":
			c = self.stack.pop()
			b = self.stack.pop()
			a = self.stack.pop()
			if a:
				self.stack.append(b)
			else:
				self.stack.append(c)

		# BASIC MATHS AND LOGIC OPERATIONS

		elif token == "+":					# 4 2 +	(places 6 on stack)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a + b)

		elif token == "-":					# 4 2 - (places 2 on stack)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a - b)

		elif token == "*":					# 4 2 * (places 8 on stack)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a * b)

		elif token == "/":					# 4 2 / (places 2 on stack, always uses integer division)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a // b)

		elif token == "%":					# 4 2 % (places 0 on stack)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a % b)

		elif token == "<":					# 4 2 < (places 0 on stack)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(1 if a < b else 0)

		elif token == ">":					# 4 2 > (places 1 on stack)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(1 if a > b else 0)

		elif token == "==":					# 4 2 == (places 0 on stack)
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(1 if a == b else 0)

		# JUMP / RETURN : jump to address at stack[-1]

		elif token == "JUMP" or token == "RETURN":
			target = self.get_address_from_item(self.stack.pop())
			self.pc = target

		# JUMPIF : if stack[-2] then jump to address at stack[-1]

		elif token == "JUMPIF":
			target = self.get_address_from_item(self.stack.pop())
			condition = self.stack.pop()
			if condition:
				self.pc = target

		# CALL : jump to address at stack[-1]

		elif token == "CALL":
			target = self.get_address_from_item(self.stack.pop())
			self.stack.append(self.pc)		# Push return address
			self.pc = self.labels[label]

		# CALLIF : if stack[-2] then jump to address at stack[-1], leaving a return address on stack

		elif token == "CALLIF":
			target = self.get_address_from_item(self.stack.pop())
			condition = self.stack.pop()
			if condition:
				self.stack.append(self.pc)	# Push return address
				self.pc = target

		# STRING LITERALS : place onto stack

		elif token.startswith('"') and token.endswith('"'):
			self.stack.append(token[1:-1])

		# STORE : save item to variable - e.g. 123 "foo" STORE

		elif token == "STORE":
			var_name = self.stack.pop()
			value = self.stack.pop()
			if not isinstance(var_name, str):
				raise TypeError("STORE: Variable identifier was not a string!")
			self.variables[var_name] = value

		# LOAD : load item from variable - e.g. "foo" LOAD

		elif token == "LOAD":
			var_name = self.stack.pop()
			if not isinstance(var_name, str):
				raise TypeError("LOAD: Variable identifier was not a string!")
			if var_name in self.variables:
				self.stack.append(self.variables[var_name])
			else:
				self.stack.append(0)			# Default to 0 for undefined variables

		# NUMERIC VALUES

		else:
			value = float(token)
			value = int(value)					# Let's say we only have ints, ever
			self.stack.append(value)

	def scan_for_enemies(self, arena):
	    # Scan for enemies in the direction of aim
	    # Simple implementation - should do raycasting?
	    min_distance = float('inf')

	    for bot in arena.bots:
	        if bot is self:
	            continue

	        # Calculate distance and angle to target
	        dx = bot.position[0] - self.position[0]
	        dy = bot.position[1] - self.position[1]
	        distance = math.sqrt(dx*dx + dy*dy)

	        # Calculate angle to target in degrees
	        # Modified to make 0 degrees point up
	        angle = (math.degrees(math.atan2(dy, dx)) + 90) % 360

	        # Check if in field of view (within 3 degrees of aim)
	        angle_diff = min((angle - self.aim_direction) % 360,
	                         (self.aim_direction - angle) % 360)

	        if angle_diff <= 3 and distance < min_distance:
	            min_distance = distance

	    return min_distance if min_distance != float('inf') else 0

	def fire_weapon(self, power, arena):
		"""Fire weapon at enemies in aim direction - creates a bullet"""
		# Create a bullet in the arena
		bullet = Bullet(
			position=self.position,
			direction=self.aim_direction,
			power=power,
			speed=10 + power,  # Bullet speed increases with power
			owner=self
		)
		arena.bullets.append(bullet)


def calculate_direction_change_cost(current, new):
	"""Calculate energy cost for direction change"""
	# Find smallest angle between directions
	diff = abs(current - new)
	if diff > 180:
		diff = 360 - diff
	return diff


class Bullet:
	def __init__(self, position, direction, power, speed, owner):
		self.position = position
		self.direction = direction
		self.power = power
		self.speed = speed
		self.owner = owner
		self.max_range = 1000
		self.distance_traveled = 0

	def move(self):
		# Move bullet according to its direction and speed
		# Modified to make 0 degrees point up
		rad = math.radians((self.direction - 90) % 360)
		dx = math.cos(rad) * self.speed
		dy = math.sin(rad) * self.speed

		x, y = self.position
		self.position = (x + dx, y + dy)
		self.distance_traveled += self.speed

	def is_expired(self):
		"""Check if bullet has reached its maximum range"""
		return self.distance_traveled >= self.max_range


class Arena:
	def __init__(self, size=(400, 400)):
		self.size = size
		self.bots = []
		self.bullets = []
		self.tick_count = 0

	def add_bot(self, code, name):
		bot = RoboBot(code, name)
		self.bots.append(bot)
		bot.position = (
			random.randint(0, self.size[0]),
			random.randint(0, self.size[1]),
		)

	def tick(self):
		"""Advance simulation by one tick"""
		self.tick_count += 1

		# Execute bot operations
		for bot in self.bots:
			bot.tick(self)

		# Move and check all bullets
		self.update_bullets()

		# Remove dead bots
		self.bots = [bot for bot in self.bots if bot.health > 0]

	def update_bullets(self):
		"""Move bullets and check for collisions"""
		# Move all bullets
		for bullet in self.bullets:
			bullet.move()

		# Check for hits
		new_bullets = []
		for bullet in self.bullets:
			# Check if bullet expired
			if bullet.is_expired():
				continue

			# Check for collisions with bots
			hit = False
			for bot in self.bots:
				# Don't hit self
				if bot is bullet.owner:
					continue

				# Check distance to bot
				dx = bot.position[0] - bullet.position[0]
				dy = bot.position[1] - bullet.position[1]
				distance = math.sqrt(dx*dx + dy*dy)

				if distance < BOT_RADIUS:
					# Hit! Calculate damage
					damage = bullet.power * (1 - bullet.distance_traveled/bullet.max_range)
					bot.health -= damage
					hit = True
					break

			# Keep bullet if no hit
			if not hit:
				new_bullets.append(bullet)

		self.bullets = new_bullets

	def is_battle_over(self):
		"""Check if battle is over (0 or 1 bots left)"""
		return len(self.bots) <= 1

	def get_winner(self):
		"""Get winner if battle is over"""
		if len(self.bots) == 1:
			return self.bots[0]
		return None



import pygame
import sys
import math
import random
import time

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
		pygame.draw.circle(self.screen, color, (x, y), BOT_RADIUS)

		# Draw tracks direction indicator
		tracks_rad = math.radians((bot.tracks_direction - 90) % 360)
		tracks_x = x + int(BOT_RADIUS * 1.5 * math.cos(tracks_rad))
		tracks_y = y + int(BOT_RADIUS * 1.5 * math.sin(tracks_rad))
		pygame.draw.line(self.screen, (200, 200, 200), (x, y), (tracks_x, tracks_y), 2)

		# Draw aim direction indicator
		aim_rad = math.radians((bot.aim_direction - 90) % 360)
		aim_x = x + int(BOT_RADIUS * 2 * math.cos(aim_rad))
		aim_y = y + int(BOT_RADIUS * 2 * math.sin(aim_rad))
		pygame.draw.line(self.screen, (255, 0, 0), (x, y), (aim_x, aim_y), 2)

		# Draw health bar
		health_width = int(BOT_RADIUS * 2 * (bot.health / 100))
		pygame.draw.rect(self.screen, (50, 50, 50),
						 (x - BOT_RADIUS, y - BOT_RADIUS - 8, BOT_RADIUS * 2, 5))
		pygame.draw.rect(self.screen, (0, 255, 0),
						 (x - BOT_RADIUS, y - BOT_RADIUS - 8, health_width, 5))

		# Draw energy bar
		energy_width = int(BOT_RADIUS * 2 * (bot.energy / 100))
		pygame.draw.rect(self.screen, (50, 50, 50),
						 (x - BOT_RADIUS, y - BOT_RADIUS - 14, BOT_RADIUS * 2, 5))
		pygame.draw.rect(self.screen, (0, 100, 255),
						 (x - BOT_RADIUS, y - BOT_RADIUS - 14, energy_width, 5))

		# Draw bot name
		name_text = self.font.render(bot.name, True, (200, 200, 200))
		self.screen.blit(name_text, (x - name_text.get_width() // 2, y + BOT_RADIUS + 5))

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
	arena = Arena()

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