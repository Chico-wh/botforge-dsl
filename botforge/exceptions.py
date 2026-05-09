"""BotForge custom exceptions."""


class BotForgeError(Exception):
    """Base exception for all BotForge errors."""
    pass


class ParseError(BotForgeError):
    """Raised when the DSL file cannot be parsed."""

    def __init__(self, message: str, lineno: int | None = None):
        self.lineno = lineno
        location = f" (line {lineno})" if lineno else ""
        super().__init__(f"Parse error{location}: {message}")


class AnalyzerError(BotForgeError):
    """Raised when the DSL uses forbidden or unsupported constructs."""

    def __init__(self, message: str, lineno: int | None = None):
        self.lineno = lineno
        location = f" (line {lineno})" if lineno else ""
        super().__init__(f"Analyzer error{location}: {message}")


class GeneratorError(BotForgeError):
    """Raised when C++ code generation fails."""
    pass


class UnsupportedTargetError(BotForgeError):
    """Raised when the requested target platform is not supported."""

    def __init__(self, target: str):
        super().__init__(
            f"Target '{target}' is not supported. "
            f"Available targets: arduino"
        )
