"""
BotForge Parser

Walks the Python AST and extracts a BotProgram IR. Never executes user code.

Supported inside @bot.loop:
  - variable assignments: distance = front.distance
  - if / elif / else chains
  - bot.forward/backward/turn_left/turn_right/stop(speed=N)
  - component.write(angle=N)   (Servo)
  - compound conditions: front.distance < 20 and front.distance > 5
"""

import ast
from pathlib import Path

from .exceptions import ParseError
from .ir import (
    ActionCall,
    BoolCondition,
    BotProgram,
    Condition,
    ConditionLeft,
    HardwareComponent,
    IfStatement,
    LoopFunction,
    SensorRead,
    VarAssign,
    VarRef,
)

# ---------------------------------------------------------------------------
# Registry: DSL component class → C++ metadata
# ---------------------------------------------------------------------------
COMPONENT_REGISTRY: dict[str, dict] = {
    "Wheels": {
        "library": "custom",
        "pin_keys": ["left", "right"],
    },
    "Ultrasonic": {
        "library": "NewPing.h",
        "pin_keys": ["trigger", "echo"],
    },
    "Servo": {
        "library": "Servo.h",
        "pin_keys": ["pin"],
    },
    "IRSensor": {
        "library": "custom",
        "pin_keys": ["pin"],
    },
    "LineSensor": {
        "library": "custom",
        "pin_keys": ["pin"],
    },
}

# Sensor kind → property name → C++ call fragment
SENSOR_PROPERTY_CPP: dict[str, dict[str, str]] = {
    "Ultrasonic": {"distance": "ping_cm()"},
    "IRSensor":   {"value": "digitalRead({pin})"},   # pin substituted at gen time
    "LineSensor": {"value": "digitalRead({pin})"},
}

# Valid bot actions inside @bot.loop
VALID_BOT_ACTIONS: set[str] = {
    "forward", "backward", "turn_left", "turn_right", "stop",
}


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
    # Top level
    # ------------------------------------------------------------------

    def _extract_program(self, tree: ast.Module) -> BotProgram:
        bot_name = self._find_bot_name(tree)
        components = self._find_components(tree)
        loop = self._find_loop(tree, components)

        if loop is None:
            raise ParseError(
                "No @bot.loop function found. "
                "Define one function decorated with @bot.loop."
            )

        return BotProgram(
            name=bot_name,
            target=self.target,
            components=components,
            loop=loop,
        )

    # ------------------------------------------------------------------
    # Bot name  — bot = Bot("name")
    # ------------------------------------------------------------------

    def _find_bot_name(self, tree: ast.Module) -> str:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not (
                isinstance(node.value, ast.Call)
                and _call_name(node.value) == "Bot"
            ):
                continue
            call = node.value
            if not call.args:
                raise ParseError(
                    "Bot() requires a name string, e.g. Bot('my_robot')",
                    node.lineno,
                )
            arg = call.args[0]
            if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                raise ParseError(
                    "Bot name must be a string literal, e.g. Bot('mini_rover')",
                    node.lineno,
                )
            return arg.value

        raise ParseError(
            "No Bot instantiation found. Expected: bot = Bot('robot_name')"
        )

    # ------------------------------------------------------------------
    # Components — bot.use(Kind(...))
    # ------------------------------------------------------------------

    def _find_components(self, tree: ast.Module) -> list[HardwareComponent]:
        components: list[HardwareComponent] = []
        seen: set[str] = set()

        for node in ast.walk(tree):
            inner = _unwrap_bot_use(node)
            if inner is None:
                continue
            comp = self._parse_component(inner, parent=node)
            if comp is None:
                continue
            if comp.name in seen:
                raise ParseError(
                    f"Duplicate component name '{comp.name}'. "
                    "Each component must have a unique name.",
                    getattr(node, "lineno", None),
                )
            seen.add(comp.name)
            components.append(comp)

        return components

    def _parse_component(
        self, call: ast.Call, parent: ast.AST
    ) -> HardwareComponent | None:
        kind = _call_name(call)
        if kind not in COMPONENT_REGISTRY:
            return None

        lineno = getattr(call, "lineno", None)

        # Name: Ultrasonic/Servo/IRSensor/LineSensor → first positional string arg
        # Wheels → assignment target variable name, or "wheels"
        name = _assignment_target_name(parent) or kind.lower()
        if kind in ("Ultrasonic", "Servo", "IRSensor", "LineSensor"):
            if not call.args:
                raise ParseError(
                    f"{kind}() needs a name as first argument, e.g. {kind}('sensor_name', ...)",
                    lineno,
                )
            first = call.args[0]
            if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                raise ParseError(f"{kind} name must be a string literal", lineno)
            name = first.value

        pins = _extract_pins(call)
        library = COMPONENT_REGISTRY[kind]["library"]

        return HardwareComponent(name=name, kind=kind, pins=pins, library=library)

    # ------------------------------------------------------------------
    # Loop function
    # ------------------------------------------------------------------

    def _find_loop(
        self, tree: ast.Module, components: list[HardwareComponent]
    ) -> LoopFunction | None:
        # Collect local variable names so we can handle VarRef in conditions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and _has_bot_loop_decorator(node):
                stmts = self._parse_statements(node.body, components, local_vars={})
                return LoopFunction(statements=stmts)
        return None

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _parse_statements(
        self,
        body: list[ast.stmt],
        components: list[HardwareComponent],
        local_vars: dict[str, str],  # varname → sensor_name for declared vars
    ) -> list:
        result = []
        for stmt in body:
            parsed = self._parse_statement(stmt, components, local_vars)
            if parsed is not None:
                result.append(parsed)
        return result

    def _parse_statement(
        self,
        stmt: ast.stmt,
        components: list[HardwareComponent],
        local_vars: dict[str, str],
    ):
        # if / elif / else
        if isinstance(stmt, ast.If):
            return self._parse_if(stmt, components, local_vars)

        # method call: bot.forward(speed=80) or arm.write(angle=90)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return self._parse_action_call(stmt.value, stmt.lineno, components)

        # variable assignment: distance = front.distance
        if isinstance(stmt, ast.Assign):
            return self._parse_var_assign(stmt, components, local_vars)

        if isinstance(stmt, ast.Pass):
            return None

        raise ParseError(
            f"Unsupported statement '{type(stmt).__name__}' inside @bot.loop. "
            "Allowed: if/elif/else, method calls (bot.forward(...)), "
            "and variable assignments (dist = sensor.distance).",
            getattr(stmt, "lineno", None),
        )

    # ------------------------------------------------------------------
    # Variable assignment: dist = front.distance
    # ------------------------------------------------------------------

    def _parse_var_assign(
        self,
        node: ast.Assign,
        components: list[HardwareComponent],
        local_vars: dict[str, str],
    ) -> VarAssign:
        lineno = node.lineno

        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise ParseError(
                "Only simple variable assignments are allowed inside @bot.loop, "
                "e.g. 'dist = front.distance'.",
                lineno,
            )
        var_name = node.targets[0].id

        # Right side must be sensor.property
        if not isinstance(node.value, ast.Attribute):
            raise ParseError(
                f"The right side of '{var_name} = ...' must be a sensor read, "
                f"e.g. '{var_name} = front.distance'.",
                lineno,
            )
        read = self._parse_sensor_attribute(node.value, lineno, components)
        local_vars[var_name] = read.sensor_name
        return VarAssign(var_name=var_name, value=read)

    # ------------------------------------------------------------------
    # if / elif / else
    # ------------------------------------------------------------------

    def _parse_if(
        self,
        node: ast.If,
        components: list[HardwareComponent],
        local_vars: dict[str, str],
    ) -> IfStatement:
        condition = self._parse_condition_expr(node.test, node.lineno, components, local_vars)
        then_body = self._parse_statements(node.body, components, local_vars)

        # elif is represented in the AST as: orelse = [If(...)]
        elif_branches = []
        else_body = []

        orelse = node.orelse
        while orelse and isinstance(orelse[0], ast.If):
            elif_node = orelse[0]
            elif_cond = self._parse_condition_expr(
                elif_node.test, elif_node.lineno, components, local_vars
            )
            elif_body = self._parse_statements(elif_node.body, components, local_vars)
            elif_branches.append((elif_cond, elif_body))
            orelse = elif_node.orelse

        if orelse:
            else_body = self._parse_statements(orelse, components, local_vars)

        return IfStatement(
            condition=condition,
            then_body=then_body,
            elif_branches=elif_branches,
            else_body=else_body,
        )

    # ------------------------------------------------------------------
    # Conditions — simple and compound (and / or)
    # ------------------------------------------------------------------

    def _parse_condition_expr(
        self,
        test: ast.expr,
        lineno: int,
        components: list[HardwareComponent],
        local_vars: dict[str, str],
    ) -> Condition | BoolCondition:
        # Compound: expr and expr  |  expr or expr
        if isinstance(test, ast.BoolOp):
            op = "and" if isinstance(test.op, ast.And) else "or"
            if len(test.values) < 2:
                raise ParseError("Boolean condition must have at least two parts", lineno)
            # Left-fold: ((a and b) and c)
            result = self._parse_condition_expr(test.values[0], lineno, components, local_vars)
            for val in test.values[1:]:
                right = self._parse_condition_expr(val, lineno, components, local_vars)
                result = BoolCondition(left=result, operator=op, right=right)
            return result

        # Simple comparison
        if isinstance(test, ast.Compare):
            return self._parse_simple_condition(test, lineno, components, local_vars)

        raise ParseError(
            "Conditions must be comparisons (e.g. front.distance < 20) "
            "or boolean combinations (e.g. front.distance < 20 and front.distance > 5).",
            lineno,
        )

    def _parse_simple_condition(
        self,
        test: ast.Compare,
        lineno: int,
        components: list[HardwareComponent],
        local_vars: dict[str, str],
    ) -> Condition:
        if len(test.ops) != 1 or len(test.comparators) != 1:
            raise ParseError(
                "Only single comparisons are supported (no chaining like a < b < c).",
                lineno,
            )

        left = self._parse_condition_left(test.left, lineno, components, local_vars)
        operator = _op_to_str(test.ops[0], lineno)

        comparator = test.comparators[0]
        if not isinstance(comparator, ast.Constant) or not isinstance(
            comparator.value, (int, float)
        ):
            raise ParseError(
                "The right side of a condition must be a numeric literal (e.g. 20).",
                lineno,
            )

        return Condition(left=left, operator=operator, right=comparator.value)

    def _parse_condition_left(
        self,
        expr: ast.expr,
        lineno: int,
        components: list[HardwareComponent],
        local_vars: dict[str, str],
    ) -> ConditionLeft:
        # sensor.property (e.g. front.distance)
        if isinstance(expr, ast.Attribute):
            return self._parse_sensor_attribute(expr, lineno, components)

        # local variable (e.g. `distance` declared via VarAssign)
        if isinstance(expr, ast.Name):
            if expr.id not in local_vars:
                raise ParseError(
                    f"'{expr.id}' is not a declared variable. "
                    "Assign it first: dist = front.distance",
                    lineno,
                )
            return VarRef(name=expr.id)

        raise ParseError(
            "The left side of a condition must be a sensor attribute "
            "(e.g. front.distance) or a declared variable.",
            lineno,
        )

    def _parse_sensor_attribute(
        self,
        expr: ast.Attribute,
        lineno: int,
        components: list[HardwareComponent],
    ) -> SensorRead:
        if not isinstance(expr.value, ast.Name):
            raise ParseError(
                "Sensor name must be a simple identifier (e.g. front.distance).",
                lineno,
            )
        sensor_name = expr.value.id
        property_name = expr.attr

        comp = next((c for c in components if c.name == sensor_name), None)
        if comp is None:
            raise ParseError(
                f"'{sensor_name}' is not a registered sensor. "
                "Register it with bot.use(...) before using it.",
                lineno,
            )

        valid_props = SENSOR_PROPERTY_CPP.get(comp.kind, {})
        if property_name not in valid_props:
            readable = ", ".join(valid_props) if valid_props else "(none yet)"
            raise ParseError(
                f"'{property_name}' is not a valid property of {comp.kind}. "
                f"Valid: {readable}",
                lineno,
            )

        return SensorRead(sensor_name=sensor_name, property_name=property_name)

    # ------------------------------------------------------------------
    # Action calls
    # ------------------------------------------------------------------

    def _parse_action_call(
        self,
        call: ast.Call,
        lineno: int,
        components: list[HardwareComponent],
    ) -> ActionCall:
        name = _call_name(call)
        if "." not in name:
            raise ParseError(
                f"Unsupported call '{name}'. Calls must be on 'bot' or a component.",
                lineno,
            )

        target, method = name.split(".", 1)

        if target == "bot":
            if method not in VALID_BOT_ACTIONS:
                raise ParseError(
                    f"'bot.{method}()' is not a supported action. "
                    f"Supported: {', '.join(sorted(VALID_BOT_ACTIONS))}.",
                    lineno,
                )
        else:
            comp = next((c for c in components if c.name == target), None)
            if comp is None:
                raise ParseError(
                    f"'{target}' is not a registered component. "
                    "Register it with bot.use(...) first.",
                    lineno,
                )
            if comp.kind == "Servo" and method != "write":
                raise ParseError(
                    f"'{method}' is not supported on Servo. Use write(angle=...).",
                    lineno,
                )

        args: dict = {}
        for kw in call.keywords:
            if not isinstance(kw.value, ast.Constant):
                raise ParseError(
                    f"Argument '{kw.arg}' must be a literal value.", lineno
                )
            args[kw.arg] = kw.value.value
        for i, arg in enumerate(call.args):
            if not isinstance(arg, ast.Constant):
                raise ParseError(
                    f"Positional argument {i + 1} must be a literal value.", lineno
                )
            args[f"_arg{i}"] = arg.value

        return ActionCall(target=target, method=method, args=args)


# ---------------------------------------------------------------------------
# Module-level AST helpers
# ---------------------------------------------------------------------------

def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    return ""


def _unwrap_bot_use(node: ast.AST) -> ast.Call | None:
    """Return the inner Call from bot.use(Component(...)), or None."""
    call_node: ast.Call | None = None
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        call_node = node.value
    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
        call_node = node.value
    if call_node is None:
        return None
    if _call_name(call_node) != "bot.use" or not call_node.args:
        return None
    arg = call_node.args[0]
    return arg if isinstance(arg, ast.Call) else None


def _assignment_target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Assign) and node.targets:
        t = node.targets[0]
        if isinstance(t, ast.Name):
            return t.id
    return None


def _extract_pins(call: ast.Call) -> dict:
    pins: dict = {}
    for kw in call.keywords:
        val = kw.value
        if isinstance(val, ast.Constant):
            pins[kw.arg] = int(val.value)
        elif isinstance(val, ast.Tuple):
            pins[kw.arg] = tuple(
                int(e.value) for e in val.elts if isinstance(e, ast.Constant)
            )
    return pins


def _has_bot_loop_decorator(func: ast.FunctionDef) -> bool:
    for dec in func.decorator_list:
        if (
            isinstance(dec, ast.Attribute)
            and isinstance(dec.value, ast.Name)
            and dec.value.id == "bot"
            and dec.attr == "loop"
        ):
            return True
    return False


def _op_to_str(op: ast.cmpop, lineno: int) -> str:
    mapping = {
        ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=",
        ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
    }
    for cls, sym in mapping.items():
        if isinstance(op, cls):
            return sym
    raise ParseError("Unsupported comparison operator.", lineno)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(path: Path, target: str = "arduino") -> BotProgram:
    return BotForgeParser(target=target).parse_file(path)
