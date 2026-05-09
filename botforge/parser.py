"""
BotForge Parser

Reads a Python DSL file, walks the native AST, and produces a BotProgram IR.
Only the controlled BotForge DSL subset is accepted; everything else raises
ParseError so users get clear feedback.
"""

import ast
from pathlib import Path

from .exceptions import ParseError
from .ir import (
    ActionCall,
    BotProgram,
    Condition,
    HardwareComponent,
    IfStatement,
    LoopFunction,
)


# ---------------------------------------------------------------------------
# Component registry: maps DSL class name -> (C++ library, required pins)
# ---------------------------------------------------------------------------
COMPONENT_REGISTRY = {
    "Wheels": {
        "library": "custom",          # Wheels is a custom generated class
        "pin_args": ["left", "right"],
    },
    "Ultrasonic": {
        "library": "NewPing.h",
        "pin_args": ["trigger", "echo"],
    },
    "Servo": {
        "library": "Servo.h",
        "pin_args": ["pin"],
    },
}

# bot.* methods that map to motor/movement actions
BOT_MOVEMENT_METHODS = {"forward", "backward", "turn_left", "turn_right", "stop"}


class BotForgeParser:
    """Parses a BotForge DSL file into a BotProgram IR."""

    def __init__(self, target: str = "arduino"):
        self.target = target

    def parse_file(self, path: Path) -> BotProgram:
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise ParseError(str(exc), exc.lineno)
        return self._extract_program(tree)

    # ------------------------------------------------------------------
    # Top-level extraction
    # ------------------------------------------------------------------

    def _extract_program(self, tree: ast.Module) -> BotProgram:
        bot_name = self._find_bot_name(tree)
        components = self._find_components(tree)
        loop = self._find_loop(tree)

        if loop is None:
            raise ParseError("No @bot.loop function found. Define a function decorated with @bot.loop.")

        return BotProgram(
            name=bot_name,
            target=self.target,
            components=components,
            loop=loop,
        )

    # ------------------------------------------------------------------
    # Bot name
    # ------------------------------------------------------------------

    def _find_bot_name(self, tree: ast.Module) -> str:
        """Find: bot = Bot("name")"""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            if not (isinstance(value, ast.Call) and self._call_name(value) == "Bot"):
                continue
            if not value.args:
                raise ParseError("Bot() requires a name argument, e.g. Bot('my_robot')")
            name_node = value.args[0]
            if not isinstance(name_node, ast.Constant):
                raise ParseError("Bot name must be a string literal")
            return str(name_node.value)

        raise ParseError("No Bot instantiation found. Expected: bot = Bot('name')")

    # ------------------------------------------------------------------
    # Components (bot.use(...))
    # ------------------------------------------------------------------

    def _find_components(self, tree: ast.Module) -> list[HardwareComponent]:
        components: list[HardwareComponent] = []

        for node in ast.walk(tree):
            # Pattern: bot.use(Component(...)) or name = bot.use(Component(...))
            call = self._unwrap_bot_use(node)
            if call is None:
                continue

            component = self._parse_component(call)
            if component:
                components.append(component)

        return components

    def _unwrap_bot_use(self, node: ast.AST) -> ast.Call | None:
        """Extract the inner Call from bot.use(Call(...))."""
        inner_call = None

        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            inner_call = node.value
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            inner_call = node.value
        else:
            return None

        if not (self._call_name(inner_call) == "bot.use" and inner_call.args):
            return None

        arg = inner_call.args[0]
        if isinstance(arg, ast.Call):
            return arg
        return None

    def _parse_component(self, call: ast.Call) -> HardwareComponent | None:
        comp_type = self._call_name(call)
        if comp_type not in COMPONENT_REGISTRY:
            return None

        registry_info = COMPONENT_REGISTRY[comp_type]

        # Determine variable name: look at the assignment target, or use type.lower()
        name = comp_type.lower()

        # For Ultrasonic / Servo: first positional arg is the name string
        if comp_type in ("Ultrasonic", "Servo") and call.args:
            first = call.args[0]
            if isinstance(first, ast.Constant):
                name = str(first.value)

        pins = self._extract_pins(call, comp_type)

        return HardwareComponent(
            name=name,
            type=comp_type,
            pins=pins,
            library=registry_info["library"],
        )

    def _extract_pins(self, call: ast.Call, comp_type: str) -> dict:
        """Extract pin numbers from keyword arguments."""
        pins = {}
        for kw in call.keywords:
            val = kw.value
            if isinstance(val, ast.Constant):
                pins[kw.arg] = int(val.value)
            elif isinstance(val, ast.Tuple):
                pins[kw.arg] = tuple(
                    int(elt.value) for elt in val.elts if isinstance(elt, ast.Constant)
                )
        return pins

    # ------------------------------------------------------------------
    # Loop function
    # ------------------------------------------------------------------

    def _find_loop(self, tree: ast.Module) -> LoopFunction | None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if self._has_bot_loop_decorator(node):
                statements = self._parse_statements(node.body)
                return LoopFunction(statements=statements)
        return None

    def _has_bot_loop_decorator(self, func: ast.FunctionDef) -> bool:
        for dec in func.decorator_list:
            if isinstance(dec, ast.Attribute):
                if (isinstance(dec.value, ast.Name) and dec.value.id == "bot"
                        and dec.attr == "loop"):
                    return True
        return False

    # ------------------------------------------------------------------
    # Statement parsing
    # ------------------------------------------------------------------

    def _parse_statements(self, body: list[ast.stmt]) -> list:
        result = []
        for stmt in body:
            parsed = self._parse_statement(stmt)
            if parsed is not None:
                result.append(parsed)
        return result

    def _parse_statement(self, stmt: ast.stmt):
        if isinstance(stmt, ast.If):
            return self._parse_if(stmt)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return self._parse_action_call(stmt.value, stmt.lineno)
        if isinstance(stmt, ast.Pass):
            return None
        raise ParseError(
            f"Unsupported statement type: {type(stmt).__name__}. "
            "Only if/else and method calls are allowed inside @bot.loop.",
            getattr(stmt, "lineno", None),
        )

    def _parse_if(self, node: ast.If) -> IfStatement:
        condition = self._parse_condition(node.test, node.lineno)
        then_body = self._parse_statements(node.body)
        else_body = self._parse_statements(node.orelse)
        return IfStatement(condition=condition, then_body=then_body, else_body=else_body)

    def _parse_condition(self, test: ast.expr, lineno: int) -> Condition:
        if not isinstance(test, ast.Compare):
            raise ParseError(
                "Only simple comparisons are supported (e.g. front.distance < 20)",
                lineno,
            )
        if len(test.ops) != 1 or len(test.comparators) != 1:
            raise ParseError("Only single comparisons are supported", lineno)

        left_str = self._expr_to_str(test.left, lineno)
        op_str = self._op_to_str(test.ops[0], lineno)
        right_str = self._expr_to_str(test.comparators[0], lineno)

        return Condition(left=left_str, operator=op_str, right=right_str)

    def _parse_action_call(self, call: ast.Call, lineno: int) -> ActionCall:
        name = self._call_name(call)
        if "." not in name:
            raise ParseError(f"Unsupported call '{name}'. Calls must be on 'bot' or a sensor.", lineno)

        target, method = name.split(".", 1)
        args = {}
        for kw in call.keywords:
            val = kw.value
            if isinstance(val, ast.Constant):
                args[kw.arg] = val.value
            else:
                raise ParseError(
                    f"Argument '{kw.arg}' must be a literal value", lineno
                )
        # Positional args (e.g. servo.write(90))
        for i, arg in enumerate(call.args):
            if isinstance(arg, ast.Constant):
                args[f"_arg{i}"] = arg.value

        return ActionCall(target=target, method=method, args=args)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _call_name(call: ast.Call) -> str:
        """Return dotted name of a Call node, e.g. 'bot.use' or 'Bot'."""
        func = call.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                return f"{func.value.id}.{func.attr}"
        return ""

    @staticmethod
    def _expr_to_str(expr: ast.expr, lineno: int) -> str:
        if isinstance(expr, ast.Constant):
            return str(expr.value)
        if isinstance(expr, ast.Name):
            return expr.id
        if isinstance(expr, ast.Attribute):
            if isinstance(expr.value, ast.Name):
                return f"{expr.value.id}.{expr.attr}"
        raise ParseError("Unsupported expression in condition", lineno)

    @staticmethod
    def _op_to_str(op: ast.cmpop, lineno: int) -> str:
        mapping = {
            ast.Lt: "<",
            ast.Gt: ">",
            ast.LtE: "<=",
            ast.GtE: ">=",
            ast.Eq: "==",
            ast.NotEq: "!=",
        }
        for cls, sym in mapping.items():
            if isinstance(op, cls):
                return sym
        raise ParseError("Unsupported comparison operator", lineno)


def parse_file(path: Path, target: str = "arduino") -> BotProgram:
    """Convenience function: parse a DSL file and return a BotProgram IR."""
    return BotForgeParser(target=target).parse_file(path)
