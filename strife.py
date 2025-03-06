import math
import random

class RoboBot:
	def __init__(self, program, name="Bot"):
		self.name = name
		self.tokens = self.tokenize(program)
		self.position = (random.randint(50, 750), random.randint(50, 750))
		self.health = 100
		self.energy = 100
		self.tracks_direction = 0  # 0-359 degrees
		self.aim_direction = 0     # 0-359 degrees
		self.speed = 0             # 0-10 units per tick
		self.active = True

		# Execution state
		self.pc = 0                # Program counter
		self.stack = []            # Data stack
		self.variables = {}        # Named variables
		self.labels = self.find_labels()

		# Limits
		self.ops_per_tick = 50
		self.ops_executed = 0

	def tokenize(self, program):
		"""Convert program string to list of tokens"""
		lines = program.strip().split("\n")
		tokens = []
		for line in lines:
			# Remove comments
			if "#" in line:
				line = line[:line.index("#")]

			# Skip empty lines
			line = line.strip()
			if not line:
				continue

			# Handle labels (lines ending with colon)
			if ":" in line and not line.startswith("#"):
				label_part = line.split(":", 1)[0].strip()
				rest_part = line.split(":", 1)[1].strip()

				# Add label as a token with colon
				tokens.append(f"{label_part}:")

				# Process rest of line if any
				if rest_part:
					tokens.extend(rest_part.split())
			else:
				# Normal line - add tokens
				tokens.extend(line.split())

		return tokens

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
		"""Execute one tick of bot operations"""
		if not self.active:
			return

		# Regenerate energy
		self.energy += 1

		# If energy is negative, don't execute
		if self.energy < 0:
			return

		# Apply movement
		self.move()

		# Reset operation counter for this tick
		self.ops_executed = 0

		# Execute operations until limit reached
		while self.ops_executed < self.ops_per_tick:
			if not self.execute_next(arena):
				break

	def move(self):
		"""Apply movement based on tracks and speed"""
		if self.speed > 0:
			# Convert direction to radians for trig functions
			rad = math.radians(self.tracks_direction)
			dx = math.cos(rad) * self.speed
			dy = math.sin(rad) * self.speed

			x, y = self.position
			new_x = x + dx
			new_y = y + dy

			# Simple boundary check (assuming 800x800 arena)
			new_x = max(0, min(800, new_x))
			new_y = max(0, min(800, new_y))

			self.position = (new_x, new_y)

	def execute_next(self, arena):
		"""Execute the next operation in the program"""
		if self.pc >= len(self.tokens):
			return False

		token = self.tokens[self.pc]
		self.pc += 1

		# Count this operation
		self.ops_executed += 1

		# Handle different operations
		if token.endswith(":") and token[:-1] in self.labels:
			return True

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

		elif token == "SETTRACKS":
			if not self.stack:
				self.active = False  # Stack underflow kills the bot
				return False

			new_direction = int(self.stack.pop()) % 360
			energy_cost = calculate_direction_change_cost(self.tracks_direction, new_direction)

			self.energy -= energy_cost
			self.tracks_direction = new_direction

		elif token == "SETAIM":
			if not self.stack:
				self.active = False
				return False

			new_direction = int(self.stack.pop()) % 360
			self.energy -= 2  # Fixed cost
			self.aim_direction = new_direction

		elif token == "SETSPEED":
			if not self.stack:
				self.active = False
				return False

			new_speed = min(10, max(0, int(self.stack.pop())))
			self.energy -= new_speed  # Cost equals new speed
			self.speed = new_speed

		elif token == "FIRE":
			if not self.stack:
				self.active = False
				return False

			power = min(10, max(1, int(self.stack.pop())))
			self.energy -= 2 * power  # Cost is 2 * power
			self.fire_weapon(power, arena)

		elif token == "DUP":
			if not self.stack:
				self.active = False
				return False

			self.stack.append(self.stack[-1])

		elif token == "DROP":
			if not self.stack:
				self.active = False
				return False

			self.stack.pop()

		elif token == "SWAP":
			if len(self.stack) < 2:
				self.active = False
				return False

			self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

		elif token == "+":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a + b)

		elif token == "-":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a - b)

		elif token == "*":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a * b)

		elif token == "/":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			if b == 0:
				self.active = False  # Division by zero kills the bot
				return False

			self.stack.append(a // b)  # Integer division

		elif token == "%":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			if b == 0:
				self.active = False  # Modulo by zero kills the bot
				return False

			self.stack.append(a % b)

		elif token == "<":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(1 if a < b else 0)

		elif token == ">":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(1 if a > b else 0)

		elif token == "=":
			if len(self.stack) < 2:
				self.active = False
				return False

			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(1 if a == b else 0)

		elif token == "JUMP" or token == "RETURN":
			if not self.stack:
				self.active = False
				return False

			label = self.stack.pop()
			# Remove quotes if present
			if isinstance(label, str):
				if label.startswith('"') and label.endswith('"'):
					label = label[1:-1]

			if label in self.labels:
				self.pc = self.labels[label]
			else:
				print(f"Error: Undefined label '{label}'")
				self.active = False
				return False

		elif token == "JUMPIF":
			if len(self.stack) < 2:
				self.active = False
				return False

			label = self.stack.pop()
			condition = self.stack.pop()

			# Remove quotes if present
			if isinstance(label, str):
				if label.startswith('"') and label.endswith('"'):
					label = label[1:-1]

			if condition:
				if label in self.labels:
					self.pc = self.labels[label]
				else:
					print(f"Error: Undefined label '{label}'")
					self.active = False
					return False

		elif token == "CALL":
			if not self.stack:
				self.active = False
				return False

			label = self.stack.pop()
			self.stack.append(self.pc)  # Push return address

			# Remove quotes if present
			if isinstance(label, str):
				if label.startswith('"') and label.endswith('"'):
					label = label[1:-1]

			if label in self.labels:
				self.pc = self.labels[label]
			else:
				print(f"Error: Undefined label '{label}'")
				self.active = False
				return False

		elif token.startswith('"') and token.endswith('"'):
			# String literal - push onto stack
			self.stack.append(token[1:-1])

		elif token == "STORE":
			if len(self.stack) < 2:
				self.active = False
				return False

			value = self.stack.pop()
			var_name = self.stack.pop()
			self.variables[var_name] = value

		elif token == "LOAD":
			if not self.stack:
				self.active = False
				return False

			var_name = self.stack.pop()
			if var_name in self.variables:
				self.stack.append(self.variables[var_name])
			else:
				self.stack.append(0)  # Default to 0 for undefined variables

		else:
			# Try to parse as a number
			try:
				value = float(token)
				if value.is_integer():
					value = int(value)
				self.stack.append(value)
			except ValueError:
				print(f"Unknown token: {token}")

		return True

	def scan_for_enemies(self, arena):
		"""Scan for enemies in the direction of aim"""
		# Simple implementation - in real game would do raycasting
		min_distance = float('inf')

		for bot in arena.bots:
			if bot is self:
				continue

			# Calculate distance and angle to target
			dx = bot.position[0] - self.position[0]
			dy = bot.position[1] - self.position[1]
			distance = math.sqrt(dx*dx + dy*dy)

			# Calculate angle to target in degrees
			angle = math.degrees(math.atan2(dy, dx))
			if angle < 0:
				angle += 360

			# Check if in field of view (within 15 degrees of aim)
			angle_diff = min((angle - self.aim_direction) % 360,
							 (self.aim_direction - angle) % 360)

			if angle_diff <= 15 and distance < min_distance:
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
		self.max_range = power * 50
		self.distance_traveled = 0

	def move(self):
		"""Move bullet according to its direction and speed"""
		rad = math.radians(self.direction)
		dx = math.cos(rad) * self.speed
		dy = math.sin(rad) * self.speed

		x, y = self.position
		self.position = (x + dx, y + dy)
		self.distance_traveled += self.speed

	def is_expired(self):
		"""Check if bullet has reached its maximum range"""
		return self.distance_traveled >= self.max_range


class Arena:
	def __init__(self, size=(800, 800)):
		self.size = size
		self.bots = []
		self.bullets = []
		self.tick_count = 0

	def add_bot(self, bot):
		self.bots.append(bot)

	def tick(self):
		"""Advance simulation by one tick"""
		self.tick_count += 1

		# Execute bot operations
		for bot in self.bots:
			bot.tick(self)

		# Move and check all bullets
		self.update_bullets()

		# Remove dead bots
		self.bots = [bot for bot in self.bots if bot.health > 0 and bot.active]

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

				# Bot radius is roughly 20 units
				if distance < 20:
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


# Example usage
if __name__ == "__main__":
	spinner_bot = """
	# Spinning turret bot
	5 SETSPEED         # Constant speed
	0 SETTRACKS        # Go straight

	main_loop:
	  AIM 10 + 360 % SETAIM  # Rotate turret
	  SCAN              # Look for enemies
	  0 >               # Found something?
	  "fire" JUMPIF     # Jump to fire if found
	  "main_loop" JUMP  # Otherwise keep scanning

	fire:
	  8 FIRE            # Fire with power 8
	  "main_loop" JUMP  # Back to scanning
	"""

	circle_bot = """
	# Circling bot
	5 SETSPEED           # Set speed

	main_loop:
	  TRACKS 3 + 360 % SETTRACKS  # Gradually turn
	  AIM 15 + 360 % SETAIM       # Spin turret faster
	  SCAN                        # Check for enemies
	  DUP 0 >                     # Found something?
	  "fire" JUMPIF               # Jump to fire if found
	  DROP                        # Clear stack
	  "main_loop" JUMP            # Loop

	fire:
	  DUP 200 <                   # Check distance
	  "high_power" JUMPIF         # High power for close targets
	  5 FIRE                      # Medium power
	  "main_loop" JUMP

	high_power:
	  DROP                        # Clear distance
	  10 FIRE                     # Full power!
	  "main_loop" JUMP
	"""

	# Create arena and bots
	arena = Arena()
	bot1 = RoboBot(spinner_bot, "Spinner")
	bot2 = RoboBot(circle_bot, "Circler")

	# Debug - print tokens and labels
	print("Tokens for Spinner:")
	for i, token in enumerate(bot1.tokens):
		print(f"  {i}: {token}")
	print("\nLabels for Spinner:")
	for label, pos in bot1.labels.items():
		print(f"  {label}: position {pos}")

	arena.add_bot(bot1)
	arena.add_bot(bot2)

	# Print initial state
	print("Starting battle with bots:")
	print(f"  - {bot1.name}: position={bot1.position}")
	print(f"  - {bot2.name}: position={bot2.position}")

	# Run simulation
	max_ticks = 1000
	for tick in range(max_ticks):
		arena.tick()

		# Print status every 100 ticks
		if tick % 100 == 0:
			print(f"Tick {tick}:")
			for bot in arena.bots:
				print(f"  - {bot.name}: health={bot.health:.1f}, energy={bot.energy:.1f}, " +
					  f"position=({bot.position[0]:.1f}, {bot.position[1]:.1f})")
			print(f"  - Active bullets: {len(arena.bullets)}")

		if arena.is_battle_over():
			break

	# Report results
	winner = arena.get_winner()
	if winner:
		print(f"Battle over after {arena.tick_count} ticks")
		print(f"Winner: {winner.name} with {winner.health:.1f} health remaining")
	else:
		print(f"Battle ended in a draw after {arena.tick_count} ticks")
