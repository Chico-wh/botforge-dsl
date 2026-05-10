"""DSL stubs for sensor components."""


class Ultrasonic:
    """HC-SR04 ultrasonic distance sensor."""
    def __init__(self, name: str, trigger: int, echo: int):
        self.name = name
        self.trigger = trigger
        self.echo = echo
        self.distance: int = 0  # IDE type hint


class IRSensor:
    """Digital IR proximity sensor (e.g. TCRT5000)."""
    def __init__(self, name: str, pin: int):
        self.name = name
        self.pin = pin
        self.value: int = 0


class LineSensor:
    """Digital line sensor (reflectance-based)."""
    def __init__(self, name: str, pin: int):
        self.name = name
        self.pin = pin
        self.value: int = 0
