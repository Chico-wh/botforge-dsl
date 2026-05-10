"""
BotForge Generator

Translates a BotProgram IR into C++ source files using Jinja2 templates.

Speed convention:
  DSL speed values are percentages (0–100).
  The generated C++ includes a normalizeSpeed() helper that converts to PWM (0–255).
  Example: speed=80 → normalizeSpeed(80) → 204 at runtime on Arduino.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .exceptions import GeneratorError, UnsupportedTargetError
from .ir import (
    ActionCall,
    BoolCondition,
    BotProgram,
    Condition,
    HardwareComponent,
    IfStatement,
    SensorRead,
    VarAssign,
    VarRef,
)


# ---------------------------------------------------------------------------
# Sensor property → C++ call fragment (per component kind)
# ---------------------------------------------------------------------------
SENSOR_PROPERTY_CPP: dict[str, dict[str, str]] = {
    "Ultrasonic": {
        "distance": "ping_cm()",
    },
    "IRSensor": {
        "value": "digitalRead({pin})",
    },
    "LineSensor": {
        "value": "digitalRead({pin})",
    },
}

# DSL bot action → C++ Wheels method
BOT_TO_WHEELS_CPP: dict[str, str] = {
    "forward":    "forward",
    "backward":   "backward",
    "turn_left":  "turnLeft",
    "turn_right": "turnRight",
    "stop":       "stop",
}


# ---------------------------------------------------------------------------
# Expression translators
# ---------------------------------------------------------------------------

def translate_sensor_read(
    read: SensorRead,
    components: list[HardwareComponent],
) -> str:
    """SensorRead("front", "distance") → "front.ping_cm()" """
    comp = next((c for c in components if c.name == read.sensor_name), None)
    if comp is None:
        raise GeneratorError(
            f"Component '{read.sensor_name}' not found in component list."
        )
    prop_map = SENSOR_PROPERTY_CPP.get(comp.kind, {})
    template = prop_map.get(read.property_name)
    if template is None:
        raise GeneratorError(
            f"No C++ mapping for {comp.kind}.{read.property_name}"
        )
    # Substitute {pin} for digital sensors
    pin = comp.pins.get("pin", 0)
    return f"{read.sensor_name}.{template.format(pin=pin)}"


def translate_condition_left(
    left,
    components: list[HardwareComponent],
) -> str:
    if isinstance(left, SensorRead):
        return translate_sensor_read(left, components)
    if isinstance(left, VarRef):
        return left.name
    raise GeneratorError(f"Unknown condition left type: {type(left)}")


def translate_condition(
    cond: Condition | BoolCondition,
    components: list[HardwareComponent],
) -> str:
    if isinstance(cond, BoolCondition):
        left_cpp = translate_condition(cond.left, components)
        right_cpp = translate_condition(cond.right, components)
        op = "&&" if cond.operator == "and" else "||"
        return f"({left_cpp} {op} {right_cpp})"
    # Simple Condition
    left_cpp = translate_condition_left(cond.left, components)
    right_val = int(cond.right) if isinstance(cond.right, float) and cond.right.is_integer() else cond.right
    return f"{left_cpp} {cond.operator} {right_val}"


def translate_action(action: ActionCall) -> str:
    """Translate an ActionCall into a C++ call string (no semicolon)."""
    target, method = action.target, action.method

    if target == "bot":
        cpp = BOT_TO_WHEELS_CPP.get(method)
        if cpp is None:
            raise GeneratorError(f"No C++ mapping for bot.{method}()")
        if method == "stop":
            return "wheels.stop()"
        speed = action.args.get("speed", 0)
        return f"wheels.{cpp}(normalizeSpeed({speed}))"

    # Servo
    if method == "write":
        angle = action.args.get("angle", action.args.get("_arg0", 0))
        return f"{target}.write({angle})"

    raise GeneratorError(f"No C++ mapping for {target}.{method}()")


# ---------------------------------------------------------------------------
# Statement renderer (recursive)
# ---------------------------------------------------------------------------

def render_statement(
    stmt,
    components: list[HardwareComponent],
    indent: int = 1,
) -> list[str]:
    pad = "    " * indent
    lines: list[str] = []

    if isinstance(stmt, VarAssign):
        cpp_val = translate_sensor_read(stmt.value, components)
        lines.append(f"{pad}int {stmt.var_name} = {cpp_val};")

    elif isinstance(stmt, ActionCall):
        lines.append(f"{pad}{translate_action(stmt)};")

    elif isinstance(stmt, IfStatement):
        cond_cpp = translate_condition(stmt.condition, components)
        lines.append(f"{pad}if ({cond_cpp}) {{")
        for s in stmt.then_body:
            lines.extend(render_statement(s, components, indent + 1))

        for elif_cond, elif_body in stmt.elif_branches:
            elif_cpp = translate_condition(elif_cond, components)
            lines.append(f"{pad}}} else if ({elif_cpp}) {{")
            for s in elif_body:
                lines.extend(render_statement(s, components, indent + 1))

        if stmt.else_body:
            lines.append(f"{pad}}} else {{")
            for s in stmt.else_body:
                lines.extend(render_statement(s, components, indent + 1))
        lines.append(f"{pad}}}")

    return lines


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class BotForgeGenerator:
    def __init__(self) -> None:
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, program: BotProgram, output_dir: Path) -> None:
        if program.target == "arduino":
            self._generate_arduino(program, output_dir)
        else:
            raise UnsupportedTargetError(program.target)

    def _generate_arduino(self, program: BotProgram, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        ctx = self._build_context(program)
        (output_dir / "main.cpp").write_text(
            self._render("arduino_main.cpp.j2", ctx), encoding="utf-8"
        )
        (output_dir / "README_GENERATED.md").write_text(
            self._render("README_GENERATED.md.j2", ctx), encoding="utf-8"
        )

    def _build_context(self, program: BotProgram) -> dict:
        wheels     = next((c for c in program.components if c.kind == "Wheels"), None)
        ultrasonics = [c for c in program.components if c.kind == "Ultrasonic"]
        servos     = [c for c in program.components if c.kind == "Servo"]
        ir_sensors = [c for c in program.components if c.kind in ("IRSensor", "LineSensor")]

        includes = ["Arduino.h"]
        if ultrasonics:
            includes.append("NewPing.h")
        if servos:
            includes.append("Servo.h")

        loop_lines: list[str] = []
        if program.loop:
            for stmt in program.loop.statements:
                loop_lines.extend(render_statement(stmt, program.components))

        return {
            "bot_name":    program.name,
            "target":      program.target,
            "includes":    includes,
            "wheels":      wheels,
            "ultrasonics": ultrasonics,
            "servos":      servos,
            "ir_sensors":  ir_sensors,
            "loop_lines":  loop_lines,
            "has_wheels":  wheels is not None,
        }

    def _render(self, name: str, ctx: dict) -> str:
        return self.env.get_template(name).render(**ctx)


def generate(program: BotProgram, output_dir: Path) -> None:
    BotForgeGenerator().generate(program, output_dir)
