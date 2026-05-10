"""
BotForge Intermediate Representation (IR)

The IR is the target-agnostic data model that sits between the AST parser
and the C++ code generator. Every node is a typed dataclass — no loose
strings for structured data.

Design decisions:
  - Condition.left is SensorRead, not a plain string.
  - Condition.right is int | float, not a string.
  - HardwareComponent uses .kind (not .type, which shadows a Python builtin).
  - VarAssign lets the loop cache sensor reads into local C++ variables.
  - BoolCondition supports `and` / `or` for compound conditions.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------

@dataclass
class HardwareComponent:
    name: str       # DSL variable name, e.g. "front"
    kind: str       # "Wheels" | "Ultrasonic" | "Servo" | "IRSensor" | "LineSensor"
    pins: dict      # e.g. {"trigger": 7, "echo": 8}
    library: str    # C++ library, e.g. "NewPing.h" or "custom"


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class SensorRead:
    """
    Represents reading a property from a sensor, e.g. `front.distance`.
    Translates to a C++ method call, e.g. `front.ping_cm()`.
    """
    sensor_name: str        # "front"
    property_name: str      # "distance"


@dataclass
class VarRef:
    """Reference to a local variable, e.g. `distance` declared via VarAssign."""
    name: str


# An expression that can appear on the left of a Condition
ConditionLeft = SensorRead | VarRef


@dataclass
class Condition:
    """Simple binary comparison: left  op  right."""
    left: ConditionLeft     # SensorRead or VarRef
    operator: str           # "<" | ">" | "<=" | ">=" | "==" | "!="
    right: int | float      # numeric literal


@dataclass
class BoolCondition:
    """Compound condition joined by 'and' or 'or'."""
    left: Condition | BoolCondition
    operator: str                       # "and" | "or"
    right: Condition | BoolCondition


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class VarAssign:
    """
    Local variable assignment inside @bot.loop, e.g.:
        distance = front.distance
    Generates:  int distance = front.ping_cm();
    """
    var_name: str
    value: SensorRead


@dataclass
class ActionCall:
    """Method call on `bot` or a named component."""
    target: str     # "bot" | "arm" | any component name
    method: str     # "forward" | "turn_left" | "write" | ...
    args: dict      # {"speed": 80} | {"angle": 90}


@dataclass
class IfStatement:
    """if / elif / else chain."""
    condition: Condition | BoolCondition
    then_body: list[Statement]
    elif_branches: list[tuple[Condition | BoolCondition, list[Statement]]]
    else_body: list[Statement]


# All statement types that can appear inside a loop body
Statement = VarAssign | ActionCall | IfStatement


# ---------------------------------------------------------------------------
# Top-level program
# ---------------------------------------------------------------------------

@dataclass
class LoopFunction:
    statements: list[Statement] = field(default_factory=list)


@dataclass
class BotProgram:
    name: str
    target: str
    components: list[HardwareComponent] = field(default_factory=list)
    loop: LoopFunction | None = None
