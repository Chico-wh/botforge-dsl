"""DSL stub: Bot class."""


class Bot:
    """
    Stub for the Bot object used in BotForge DSL files.

    At compile time the BotForge parser reads this object's usage from the
    AST. At runtime (if the user happens to run the file directly) the stubs
    just do nothing, which prevents ImportError.
    """

    def __init__(self, name: str):
        self.name = name
        self._components: list = []

    def use(self, component):
        """Register a hardware component with this bot."""
        self._components.append(component)
        return component

    def loop(self, func):
        """Decorator: mark a function as the main robot loop."""
        return func

    # Movement stubs — only executed if the file is run directly
    def forward(self, speed: int = 100): ...
    def backward(self, speed: int = 100): ...
    def turn_left(self, speed: int = 100): ...
    def turn_right(self, speed: int = 100): ...
    def stop(self): ...
