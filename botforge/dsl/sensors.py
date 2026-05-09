"""DSL stubs: sensor components."""


class Ultrasonic:
    """Stub for an HC-SR04 ultrasonic distance sensor."""

    def __init__(self, name: str, trigger: int, echo: int):
        self.name = name
        self.trigger = trigger
        self.echo = echo
        self.distance: int = 0  # type hint for user IDE support
