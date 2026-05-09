"""Tests for botforge.parser — DSL AST parsing."""

import pytest
from pathlib import Path

from botforge.parser import parse_file
from botforge.ir import BotProgram, HardwareComponent, LoopFunction
from botforge.exceptions import ParseError


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_source(source: str, target: str = "arduino") -> BotProgram:
    """Parse a DSL string directly (write to tmp file)."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(source)
        tmp = Path(f.name)
    try:
        return parse_file(tmp, target=target)
    finally:
        os.unlink(tmp)


OBSTACLE_SOURCE = """\
from botforge import Bot, Wheels, Ultrasonic

bot = Bot("mini_rover")
bot.use(Wheels(left=(5, 6), right=(9, 10)))
front = bot.use(Ultrasonic("front", trigger=7, echo=8))

@bot.loop
def main():
    if front.distance < 20:
        bot.turn_left(speed=50)
    else:
        bot.forward(speed=80)
"""


# ---------------------------------------------------------------------------
# Bot detection
# ---------------------------------------------------------------------------

def test_parser_detects_bot_name():
    program = parse_source(OBSTACLE_SOURCE)
    assert program.name == "mini_rover"


def test_parser_target_is_set():
    program = parse_source(OBSTACLE_SOURCE, target="arduino")
    assert program.target == "arduino"


# ---------------------------------------------------------------------------
# Wheels detection
# ---------------------------------------------------------------------------

def test_parser_detects_wheels():
    program = parse_source(OBSTACLE_SOURCE)
    wheels = next((c for c in program.components if c.type == "Wheels"), None)
    assert wheels is not None, "Wheels component not found"


def test_parser_wheels_pins():
    program = parse_source(OBSTACLE_SOURCE)
    wheels = next(c for c in program.components if c.type == "Wheels")
    assert wheels.pins["left"] == (5, 6)
    assert wheels.pins["right"] == (9, 10)


# ---------------------------------------------------------------------------
# Ultrasonic detection
# ---------------------------------------------------------------------------

def test_parser_detects_ultrasonic():
    program = parse_source(OBSTACLE_SOURCE)
    sensors = [c for c in program.components if c.type == "Ultrasonic"]
    assert len(sensors) == 1


def test_parser_ultrasonic_name():
    program = parse_source(OBSTACLE_SOURCE)
    sensor = next(c for c in program.components if c.type == "Ultrasonic")
    assert sensor.name == "front"


def test_parser_ultrasonic_pins():
    program = parse_source(OBSTACLE_SOURCE)
    sensor = next(c for c in program.components if c.type == "Ultrasonic")
    assert sensor.pins["trigger"] == 7
    assert sensor.pins["echo"] == 8


# ---------------------------------------------------------------------------
# Loop detection
# ---------------------------------------------------------------------------

def test_parser_detects_bot_loop():
    program = parse_source(OBSTACLE_SOURCE)
    assert program.loop is not None
    assert isinstance(program.loop, LoopFunction)


def test_parser_loop_has_statements():
    program = parse_source(OBSTACLE_SOURCE)
    assert len(program.loop.statements) > 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_parser_raises_without_bot():
    with pytest.raises(ParseError, match="No Bot instantiation"):
        parse_source("from botforge import Bot\n\n@lambda: None\ndef main(): pass\n")


def test_parser_raises_without_loop():
    source = """\
from botforge import Bot
bot = Bot("test")
def main():
    pass
"""
    with pytest.raises(ParseError, match="No @bot.loop"):
        parse_source(source)


# ---------------------------------------------------------------------------
# Example file integration test
# ---------------------------------------------------------------------------

def test_parse_obstacle_avoidance_example():
    path = EXAMPLES_DIR / "obstacle_avoidance.py"
    program = parse_file(path, target="arduino")
    assert program.name == "mini_rover"
    assert program.loop is not None
    assert any(c.type == "Wheels" for c in program.components)
    assert any(c.type == "Ultrasonic" for c in program.components)
