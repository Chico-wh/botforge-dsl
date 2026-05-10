"""BotForge — Python DSL compiler for robot C++ code generation."""

__version__ = "0.2.0"
__author__ = "Felipe Santos"

# Re-export DSL API so users can write:
#   from botforge import Bot, Wheels, Ultrasonic, Servo, IRSensor, LineSensor
from botforge.dsl.bot import Bot
from botforge.dsl.wheels import Wheels
from botforge.dsl.sensors import Ultrasonic, IRSensor, LineSensor
from botforge.dsl.servo import Servo

__all__ = ["Bot", "Wheels", "Ultrasonic", "Servo", "IRSensor", "LineSensor"]
