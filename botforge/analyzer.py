"""
BotForge Analyzer

Validates the raw Python AST *before* IR extraction to enforce DSL rules.
Raises AnalyzerError for any forbidden construct so users get clear messages.

This is a separate pass over the AST (not the IR) because some checks are
easier to do on the raw tree (e.g. detecting 'while', 'for', 'lambda').
"""

import ast
from pathlib import Path

from .exceptions import AnalyzerError

# ---------------------------------------------------------------------------
# Forbidden node types with user-friendly names
# ---------------------------------------------------------------------------
FORBIDDEN_NODES: dict[type[ast.AST], str] = {
    ast.While: "while loops",
    ast.For: "for loops",
    ast.AsyncFunctionDef: "async functions",
    ast.AsyncFor: "async for loops",
    ast.AsyncWith: "async with blocks",
    ast.Lambda: "lambda expressions",
    ast.ClassDef: "class definitions",
    ast.Global: "global statements",
    ast.Nonlocal: "nonlocal statements",
    ast.Delete: "del statements",
    ast.Yield: "yield expressions",
    ast.YieldFrom: "yield from expressions",
    ast.Await: "await expressions",
}

# Allowed import: only 'from botforge import ...'
ALLOWED_IMPORT_MODULE = "botforge"

# Methods that are valid on 'bot'
VALID_BOT_METHODS = {
    "forward", "backward", "turn_left", "turn_right", "stop", "use", "loop"
}

# Valid top-level callable names
VALID_CALLABLES = {"Bot", "Wheels", "Ultrasonic", "Servo", "bot.use", "bot.forward",
                   "bot.backward", "bot.turn_left", "bot.turn_right", "bot.stop"}


class BotForgeAnalyzer:
    """Walks the Python AST and enforces DSL rules."""

    def analyze_file(self, path: Path) -> None:
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise AnalyzerError(str(exc), exc.lineno)
        self.analyze_tree(tree)

    def analyze_tree(self, tree: ast.Module) -> None:
        self._check_forbidden_nodes(tree)
        self._check_imports(tree)
        self._check_nested_functions(tree)

    # ------------------------------------------------------------------
    # Forbidden construct detection
    # ------------------------------------------------------------------

    def _check_forbidden_nodes(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            for forbidden_type, label in FORBIDDEN_NODES.items():
                if isinstance(node, forbidden_type):
                    lineno = getattr(node, "lineno", None)
                    raise AnalyzerError(
                        f"'{label}' are not allowed in BotForge DSL.", lineno
                    )

    # ------------------------------------------------------------------
    # Import validation
    # ------------------------------------------------------------------

    def _check_imports(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                raise AnalyzerError(
                    "Plain 'import' statements are not allowed. "
                    "Use: from botforge import Bot, Wheels, Ultrasonic",
                    getattr(node, "lineno", None),
                )
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module != ALLOWED_IMPORT_MODULE:
                    raise AnalyzerError(
                        f"Importing from '{module}' is not allowed. "
                        f"Only 'from botforge import ...' is permitted.",
                        getattr(node, "lineno", None),
                    )

    # ------------------------------------------------------------------
    # No nested function definitions
    # ------------------------------------------------------------------

    def _check_nested_functions(self, tree: ast.Module) -> None:
        """Functions defined inside other functions are not allowed."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if child is node:
                        continue
                    if isinstance(child, ast.FunctionDef):
                        raise AnalyzerError(
                            f"Nested function '{child.name}' is not allowed. "
                            "Define all functions at the top level.",
                            getattr(child, "lineno", None),
                        )


def analyze_file(path: Path) -> None:
    """Convenience function: analyze a DSL file."""
    BotForgeAnalyzer().analyze_file(path)


def analyze_tree(tree: ast.Module) -> None:
    """Convenience function: analyze an already-parsed AST."""
    BotForgeAnalyzer().analyze_tree(tree)
