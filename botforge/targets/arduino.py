"""
Arduino target definition.

Contains metadata and configuration for the Arduino compilation target.
When adding a new target (ESP32, ROS 2), create a new file here and
register it in generator.py.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ArduinoTarget:
    name: str = "arduino"
    display_name: str = "Arduino"
    description: str = "Arduino Uno / Mega / Nano"
    file_extension: str = ".cpp"
    supported_components: tuple = ("Wheels", "Ultrasonic", "Servo")
    required_core_includes: tuple = ("Arduino.h",)

    # Library -> install URL mapping (for generated documentation)
    library_urls: dict = None

    def __post_init__(self):
        object.__setattr__(self, "library_urls", {
            "NewPing.h": "https://github.com/livetronic/NewPing",
            "Servo.h": "Built-in Arduino library",
        })


ARDUINO = ArduinoTarget()
