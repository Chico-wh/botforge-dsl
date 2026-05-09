"""
BotForge Generator

Takes a BotProgram IR and renders C++ code using Jinja2 templates.
Each target (arduino, esp32, ros2) will have its own rendering logic.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .exceptions import GeneratorError, UnsupportedTargetError
from .ir import ActionCall, BotProgram, HardwareComponent, IfStatement


# ---------------------------------------------------------------------------
# DSL -> C++ translation helpers
# ---------------------------------------------------------------------------

# Maps sensor attribute access to C++ method calls
SENSOR_READ_MAP = {
    "distance": "ping_cm()",
}

# Maps bot movement methods to Wheels C++ methods
BOT_TO_WHEELS_MAP = {
    "forward": "forward",
    "backward": "backward",
    "turn_left": "turnLeft",
    "turn_right": "turnRight",
    "stop": "stop",
}


def translate_condition_left(left: str, components: list[HardwareComponent]) -> str:
    """Translate 'front.distance' -> 'front.ping_cm()'."""
    if "." not in left:
        return left
    obj, attr = left.split(".", 1)
    # Check if the object is a known sensor component
    comp = next((c for c in components if c.name == obj), None)
    if comp and comp.type == "Ultrasonic":
        cpp_method = SENSOR_READ_MAP.get(attr, attr)
        return f"{obj}.{cpp_method}"
    return left


def translate_action(action: ActionCall) -> str:
    """Translate an ActionCall IR node into a C++ statement string."""
    target = action.target
    method = action.method

    if target == "bot":
        cpp_method = BOT_TO_WHEELS_MAP.get(method)
        if cpp_method is None:
            raise GeneratorError(f"Unknown bot method: '{method}'")
        if method == "stop":
            return "wheels.stop()"
        speed = action.args.get("speed", 0)
        return f"wheels.{cpp_method}({speed})"

    # Servo or other component
    if method == "write":
        angle = action.args.get("angle", action.args.get("_arg0", 0))
        return f"{target}.write({angle})"

    raise GeneratorError(f"Cannot translate action: {target}.{method}()")


def render_statement(stmt, components: list[HardwareComponent], indent: int = 1) -> list[str]:
    """Recursively render a statement (ActionCall or IfStatement) into C++ lines."""
    pad = "    " * indent
    lines = []

    if isinstance(stmt, ActionCall):
        lines.append(f"{pad}{translate_action(stmt)};")

    elif isinstance(stmt, IfStatement):
        cond = stmt.condition
        left_cpp = translate_condition_left(cond.left, components)
        lines.append(f"{pad}if ({left_cpp} {cond.operator} {cond.right}) {{")
        for s in stmt.then_body:
            lines.extend(render_statement(s, components, indent + 1))
        if stmt.else_body:
            lines.append(f"{pad}}} else {{")
            for s in stmt.else_body:
                lines.extend(render_statement(s, components, indent + 1))
        lines.append(f"{pad}}}")

    return lines


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class BotForgeGenerator:
    """Renders a BotProgram IR into output files for a specific target."""

    def __init__(self):
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

    # ------------------------------------------------------------------
    # Arduino target
    # ------------------------------------------------------------------

    def _generate_arduino(self, program: BotProgram, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        context = self._build_arduino_context(program)

        # main.cpp
        cpp_path = output_dir / "main.cpp"
        cpp_path.write_text(self._render("arduino_main.cpp.j2", context), encoding="utf-8")

        # README_GENERATED.md
        readme_path = output_dir / "README_GENERATED.md"
        readme_path.write_text(self._render("README_GENERATED.md.j2", context), encoding="utf-8")

    def _build_arduino_context(self, program: BotProgram) -> dict:
        wheels = next((c for c in program.components if c.type == "Wheels"), None)
        ultrasonics = [c for c in program.components if c.type == "Ultrasonic"]
        servos = [c for c in program.components if c.type == "Servo"]

        includes = ["Arduino.h"]
        if ultrasonics:
            includes.append("NewPing.h")
        if servos:
            includes.append("Servo.h")

        loop_lines = []
        if program.loop:
            for stmt in program.loop.statements:
                loop_lines.extend(render_statement(stmt, program.components))

        return {
            "bot_name": program.name,
            "target": program.target,
            "includes": includes,
            "wheels": wheels,
            "ultrasonics": ultrasonics,
            "servos": servos,
            "loop_lines": loop_lines,
            "has_wheels": wheels is not None,
        }

    def _render(self, template_name: str, context: dict) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)


def generate(program: BotProgram, output_dir: Path) -> None:
    """Convenience function: generate code for a BotProgram."""
    BotForgeGenerator().generate(program, output_dir)
