"""
BotForge Analyzer

First pass over the raw Python AST. Enforces structural DSL rules before
the parser builds the IR. Reports violations with file, line, and a clear
explanation of what is allowed instead.

This module never executes user code — AST inspection only.
"""

import ast
from pathlib import Path

from .exceptions import AnalyzerError

# ---------------------------------------------------------------------------
# Forbidden AST node types
# ---------------------------------------------------------------------------
FORBIDDEN_NODES: dict[type[ast.AST], str] = {
    ast.While:            "while loops",
    ast.For:              "for loops",
    ast.AsyncFunctionDef: "async functions",
    ast.AsyncFor:         "async for loops",
    ast.AsyncWith:        "async with blocks",
    ast.Lambda:           "lambda expressions",
    ast.ClassDef:         "class definitions",
    ast.Global:           "global statements",
    ast.Nonlocal:         "nonlocal statements",
    ast.Delete:           "del statements",
    ast.Yield:            "yield expressions",
    ast.YieldFrom:        "yield from expressions",
    ast.Await:            "await expressions",
    ast.Try:              "try/except blocks",
    ast.With:             "with statements",
    ast.ListComp:         "list comprehensions",
    ast.SetComp:          "set comprehensions",
    ast.DictComp:         "dict comprehensions",
    ast.GeneratorExp:     "generator expressions",
    ast.Raise:            "raise statements",
    ast.Assert:           "assert statements",
}

# Functions that must never be called
FORBIDDEN_CALLS: set[str] = {
    "eval", "exec", "compile", "__import__",
    "open", "vars", "locals", "globals", "dir",
    "getattr", "setattr", "delattr", "hasattr",
}

# Only this import module is allowed
ALLOWED_IMPORT_MODULE = "botforge"

# Valid methods callable on `bot` inside @bot.loop
VALID_BOT_LOOP_METHODS: set[str] = {
    "forward", "backward", "turn_left", "turn_right", "stop",
}

# Valid methods on known component types
VALID_COMPONENT_METHODS: dict[str, set[str]] = {
    "Servo":      {"write"},
    "Ultrasonic": set(),   # only attribute reads, no method calls
    "IRSensor":   set(),
    "LineSensor": set(),
}

# Component kinds that can appear inside bot.use()
KNOWN_COMPONENT_KINDS: set[str] = {
    "Wheels", "Ultrasonic", "Servo", "IRSensor", "LineSensor",
}


class BotForgeAnalyzer:
    """Walks the Python AST and enforces all DSL rules."""

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
        self._check_forbidden_calls(tree)
        self._check_nested_functions(tree)
        self._check_bot_methods_in_loop(tree)
        self._check_unknown_bot_use_components(tree)

    # ------------------------------------------------------------------
    # 1. Forbidden node types
    # ------------------------------------------------------------------

    def _check_forbidden_nodes(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            for forbidden_cls, label in FORBIDDEN_NODES.items():
                if isinstance(node, forbidden_cls):
                    lineno = getattr(node, "lineno", None)
                    raise AnalyzerError(
                        f"'{label}' are not supported in BotForge DSL. "
                        "Only if/else, variable assignments, and method calls "
                        "are allowed inside @bot.loop.",
                        lineno,
                    )

    # ------------------------------------------------------------------
    # 2. Imports
    # ------------------------------------------------------------------

    def _check_imports(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                raise AnalyzerError(
                    "Plain 'import' statements are not allowed. "
                    "Only 'from botforge import ...' is permitted.",
                    getattr(node, "lineno", None),
                )
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module != ALLOWED_IMPORT_MODULE:
                    raise AnalyzerError(
                        f"Importing from '{node.module}' is not allowed. "
                        "Only 'from botforge import Bot, Wheels, ...' is permitted.",
                        getattr(node, "lineno", None),
                    )

    # ------------------------------------------------------------------
    # 3. Forbidden function calls (eval, exec, open, ...)
    # ------------------------------------------------------------------

    def _check_forbidden_calls(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            if name in FORBIDDEN_CALLS:
                raise AnalyzerError(
                    f"'{name}()' is not allowed in BotForge DSL.",
                    getattr(node, "lineno", None),
                )

    # ------------------------------------------------------------------
    # 4. No nested function definitions
    # ------------------------------------------------------------------

    def _check_nested_functions(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for child in ast.walk(node):
                if child is node:
                    continue
                if isinstance(child, ast.FunctionDef):
                    raise AnalyzerError(
                        f"Nested function '{child.name}' is not allowed. "
                        "All functions must be defined at the top level.",
                        getattr(child, "lineno", None),
                    )

    # ------------------------------------------------------------------
    # 5. bot.* method calls inside @bot.loop must be valid
    # ------------------------------------------------------------------

    def _check_bot_methods_in_loop(self, tree: ast.Module) -> None:
        loop_func = _find_loop_function(tree)
        if loop_func is None:
            return
        for node in ast.walk(loop_func):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "bot"
            ):
                continue
            method = func.attr
            if method not in VALID_BOT_LOOP_METHODS:
                raise AnalyzerError(
                    f"'bot.{method}()' is not a supported action. "
                    f"Supported: {', '.join(sorted(VALID_BOT_LOOP_METHODS))}.",
                    getattr(node, "lineno", None),
                )

    # ------------------------------------------------------------------
    # 6. bot.use() must receive a known component
    # ------------------------------------------------------------------

    def _check_unknown_bot_use_components(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            # Accept both:  bot.use(X(...))  and  y = bot.use(X(...))
            call_node: ast.Call | None = None
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call_node = node.value
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call_node = node.value

            if call_node is None:
                continue
            func = call_node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "bot"
                and func.attr == "use"
            ):
                continue
            if not call_node.args:
                continue
            inner = call_node.args[0]
            if not isinstance(inner, ast.Call):
                continue
            comp_name = ""
            if isinstance(inner.func, ast.Name):
                comp_name = inner.func.id
            if comp_name and comp_name not in KNOWN_COMPONENT_KINDS:
                raise AnalyzerError(
                    f"'{comp_name}' is not a known BotForge component. "
                    f"Supported: {', '.join(sorted(KNOWN_COMPONENT_KINDS))}.",
                    getattr(inner, "lineno", None),
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_loop_function(tree: ast.Module) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if (
                isinstance(dec, ast.Attribute)
                and isinstance(dec.value, ast.Name)
                and dec.value.id == "bot"
                and dec.attr == "loop"
            ):
                return node
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_file(path: Path) -> None:
    BotForgeAnalyzer().analyze_file(path)


def analyze_tree(tree: ast.Module) -> None:
    BotForgeAnalyzer().analyze_tree(tree)
