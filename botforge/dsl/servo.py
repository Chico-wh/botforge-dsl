"""DSL stub: Servo component."""


class Servo:
    """Stub for a standard PWM servo motor."""

    def __init__(self, name: str, pin: int):
        self.name = name
        self.pin = pin

    def write(self, angle: int): ...
