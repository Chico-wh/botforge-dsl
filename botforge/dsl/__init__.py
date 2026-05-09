"""
BotForge DSL public API.

Users import from here:
    from botforge import Bot, Wheels, Ultrasonic, Servo

At runtime these are lightweight stub objects. Their only job is to
allow the user's .py file to be imported (for linting/type checking)
without errors. The actual behavior is defined by the compiler, not
by executing these stubs.
"""

from .bot import Bot
from .sensors import Ultrasonic
from .servo import Servo
from .wheels import Wheels

__all__ = ["Bot", "Wheels", "Ultrasonic", "Servo"]
