import math
import random
import sys

class RoboBot:
	def __init__(self, program, name="Bot"):
		self.name = name
		self.tokens = self.tokenize(program)
		self.position = (0, 0)		# To be set from outside
		self.health = 100
		self.energy = 100
		self.tracks_direction = 0  # 0-359 degrees
		self.aim_direction = 0     # 0-359 degrees
		self.speed = 0             # 0-10 units per tick

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
		try:

			if self.health <= 0:
				return
			self.energy += 1
			if self.energy < 0:
				return
			self.move(arena)
			self.ops_executed = 0			# Reset for this tick
			while self.ops_executed < self.ops_per_tick:
				self.execute_next(arena)

		except Exception as e:
			print(self.name, e)
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



def main():

	arena = Arena()

	for filename in sys.argv[1:]:
		with open(filename, encoding = "utf-8") as infile:
			code = infile.read()
			arena.add_bot(code, filename)

	# Run simulation
	max_ticks = 1000
	for tick in range(max_ticks):
		arena.tick()

		# Print status every 100 ticks
		if tick % 100 == 0:
			print(f"Tick {tick}:")
			for bot in arena.bots:
				print(f"  - {bot.name}: health={bot.health:.1f}, energy={bot.energy:.1f}, aim={bot.aim_direction} " +
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


if __name__ == "__main__":
	main()
