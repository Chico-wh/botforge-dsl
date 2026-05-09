"""
Intermediate Representation (IR) for BotForge.

The IR sits between the parsed AST and the C++ code generator.
It is a clean, target-agnostic description of the robot program.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Hardware components
# ---------------------------------------------------------------------------

@dataclass
class HardwareComponent:
    """Represents a physical hardware component attached to the robot."""
    name: str           # variable name used in user code (e.g. "front")
    type: str           # component type: "Wheels", "Ultrasonic", "Servo"
    pins: dict          # pin mapping, e.g. {"trigger": 7, "echo": 8}
    library: str        # C++ library required, e.g. "NewPing.h"


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

@dataclass
class Condition:
    """A simple binary comparison: left op right."""
    left: str           # e.g. "front.distance"
    operator: str       # e.g. "<", ">", "==", "!="
    right: str          # e.g. "20"


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class ActionCall:
    """A method call on a robot component or the bot itself."""
    target: str         # e.g. "bot" or "servo1"
    method: str         # e.g. "forward", "turn_left", "write"
    args: dict          # keyword args, e.g. {"speed": 80}


@dataclass
class IfStatement:
    """An if/else branch."""
    condition: Condition
    then_body: list     # list of ActionCall | IfStatement
    else_body: list     # list of ActionCall | IfStatement (may be empty)


# Union type for any statement inside loop
Statement = ActionCall | IfStatement


# ---------------------------------------------------------------------------
# Top-level program
# ---------------------------------------------------------------------------

@dataclass
class LoopFunction:
    """The @bot.loop decorated function body."""
    statements: list[Statement] = field(default_factory=list)


@dataclass
class BotProgram:
    """Root IR node: represents the entire robot program."""
    name: str                               # robot name, e.g. "mini_rover"
    target: str                             # compilation target, e.g. "arduino"
    components: list[HardwareComponent] = field(default_factory=list)
    loop: LoopFunction | None = None
