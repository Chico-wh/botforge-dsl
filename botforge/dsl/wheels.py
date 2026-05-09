"""DSL stub: Wheels component."""


class Wheels:
    """Stub for a two-motor differential drive setup."""

    def __init__(self, left: tuple[int, int], right: tuple[int, int]):
        self.left = left
        self.right = right
