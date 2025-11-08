def factorial(n):
	"""Calculate factorial of n."""
	if n <= 1:
		return 1
	else:
		return n * factorial(n - 1)


class TestClass:
	"""A simple test class."""

	def __init__(self, value):
		self.value = value
		self.count = 0

	def increment(self):
		"""Increment the counter."""
		self.count += 1
		return self.count

	def get_value(self):
		"""Get the current value."""
		return self.value


# Main execution
if __name__ == '__main__':
	# Test factorial
	print("Factorial of 5:", factorial(5))

	# Test class
	obj = TestClass(42)
	print("Initial value:", obj.get_value())
	print("Count after increment:", obj.increment())
	print("Count after increment:", obj.increment())
