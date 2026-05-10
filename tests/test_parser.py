"""Tests for botforge.parser"""

import os, tempfile
import pytest
from pathlib import Path

from botforge.parser import parse_file
from botforge.ir import (
    BotProgram, HardwareComponent, LoopFunction,
    IfStatement, ActionCall, Condition, BoolCondition,
    SensorRead, VarRef, VarAssign,
)
from botforge.exceptions import ParseError

EXAMPLES = Path(__file__).parent.parent / "examples"


def parse(source: str, target: str = "arduino") -> BotProgram:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(source)
        p = Path(f.name)
    try:
        return parse_file(p, target=target)
    finally:
        os.unlink(p)


OBSTACLE_SRC = """\
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
# Bot name
# ---------------------------------------------------------------------------

def test_bot_name():
    assert parse(OBSTACLE_SRC).name == "mini_rover"

def test_bot_target():
    assert parse(OBSTACLE_SRC, "arduino").target == "arduino"


# ---------------------------------------------------------------------------
# Wheels
# ---------------------------------------------------------------------------

def test_detects_wheels():
    prog = parse(OBSTACLE_SRC)
    assert any(c.kind == "Wheels" for c in prog.components)

def test_wheels_pins():
    prog = parse(OBSTACLE_SRC)
    w = next(c for c in prog.components if c.kind == "Wheels")
    assert w.pins["left"] == (5, 6)
    assert w.pins["right"] == (9, 10)

def test_wheels_uses_kind_not_type():
    prog = parse(OBSTACLE_SRC)
    w = next(c for c in prog.components if c.kind == "Wheels")
    assert hasattr(w, "kind")
    assert not hasattr(w, "type") or w.kind == "Wheels"


# ---------------------------------------------------------------------------
# Ultrasonic
# ---------------------------------------------------------------------------

def test_detects_ultrasonic():
    prog = parse(OBSTACLE_SRC)
    assert any(c.kind == "Ultrasonic" for c in prog.components)

def test_ultrasonic_name():
    prog = parse(OBSTACLE_SRC)
    s = next(c for c in prog.components if c.kind == "Ultrasonic")
    assert s.name == "front"

def test_ultrasonic_pins():
    prog = parse(OBSTACLE_SRC)
    s = next(c for c in prog.components if c.kind == "Ultrasonic")
    assert s.pins["trigger"] == 7
    assert s.pins["echo"] == 8


# ---------------------------------------------------------------------------
# @bot.loop
# ---------------------------------------------------------------------------

def test_detects_loop():
    prog = parse(OBSTACLE_SRC)
    assert prog.loop is not None
    assert isinstance(prog.loop, LoopFunction)

def test_loop_has_statements():
    prog = parse(OBSTACLE_SRC)
    assert len(prog.loop.statements) > 0


# ---------------------------------------------------------------------------
# Condition is structured (SensorRead, typed right)
# ---------------------------------------------------------------------------

def test_condition_uses_sensor_read():
    prog = parse(OBSTACLE_SRC)
    stmt = prog.loop.statements[0]
    assert isinstance(stmt, IfStatement)
    cond = stmt.condition
    assert isinstance(cond, Condition)
    assert isinstance(cond.left, SensorRead), (
        f"Condition.left should be SensorRead, got {type(cond.left)}"
    )

def test_condition_sensor_name():
    prog = parse(OBSTACLE_SRC)
    cond = prog.loop.statements[0].condition
    assert cond.left.sensor_name == "front"
    assert cond.left.property_name == "distance"

def test_condition_right_is_int():
    prog = parse(OBSTACLE_SRC)
    cond = prog.loop.statements[0].condition
    assert isinstance(cond.right, (int, float)), (
        f"Condition.right should be int/float, got {type(cond.right)}"
    )
    assert cond.right == 20

def test_condition_operator():
    prog = parse(OBSTACLE_SRC)
    assert prog.loop.statements[0].condition.operator == "<"


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def test_action_turn_left():
    prog = parse(OBSTACLE_SRC)
    stmt = prog.loop.statements[0]
    action = stmt.then_body[0]
    assert isinstance(action, ActionCall)
    assert action.target == "bot"
    assert action.method == "turn_left"
    assert action.args["speed"] == 50

def test_action_forward():
    prog = parse(OBSTACLE_SRC)
    stmt = prog.loop.statements[0]
    action = stmt.else_body[0]
    assert action.method == "forward"
    assert action.args["speed"] == 80


# ---------------------------------------------------------------------------
# Variable assignment
# ---------------------------------------------------------------------------

def test_var_assign():
    src = """\
from botforge import Bot, Wheels, Ultrasonic
bot = Bot("r")
bot.use(Wheels(left=(1,2), right=(3,4)))
front = bot.use(Ultrasonic("front", trigger=5, echo=6))
@bot.loop
def main():
    dist = front.distance
    if front.distance < 20:
        bot.stop()
"""
    prog = parse(src)
    first = prog.loop.statements[0]
    assert isinstance(first, VarAssign)
    assert first.var_name == "dist"
    assert isinstance(first.value, SensorRead)
    assert first.value.sensor_name == "front"


# ---------------------------------------------------------------------------
# elif chains
# ---------------------------------------------------------------------------

def test_elif_chain():
    src = """\
from botforge import Bot, Wheels, Ultrasonic
bot = Bot("r")
bot.use(Wheels(left=(1,2), right=(3,4)))
front = bot.use(Ultrasonic("front", trigger=5, echo=6))
@bot.loop
def main():
    if front.distance < 10:
        bot.stop()
    elif front.distance < 30:
        bot.turn_left(speed=40)
    else:
        bot.forward(speed=80)
"""
    prog = parse(src)
    stmt = prog.loop.statements[0]
    assert isinstance(stmt, IfStatement)
    assert len(stmt.elif_branches) == 1
    elif_cond, elif_body = stmt.elif_branches[0]
    assert isinstance(elif_cond, Condition)
    assert elif_cond.right == 30


# ---------------------------------------------------------------------------
# Compound conditions (and / or)
# ---------------------------------------------------------------------------

def test_compound_condition_and():
    src = """\
from botforge import Bot, Wheels, Ultrasonic
bot = Bot("r")
bot.use(Wheels(left=(1,2), right=(3,4)))
front = bot.use(Ultrasonic("front", trigger=5, echo=6))
@bot.loop
def main():
    if front.distance < 30 and front.distance > 5:
        bot.forward(speed=60)
"""
    prog = parse(src)
    stmt = prog.loop.statements[0]
    assert isinstance(stmt.condition, BoolCondition)
    assert stmt.condition.operator == "and"


# ---------------------------------------------------------------------------
# Multiple sensors
# ---------------------------------------------------------------------------

def test_multiple_sensors():
    src = """\
from botforge import Bot, Wheels, Ultrasonic
bot = Bot("r")
bot.use(Wheels(left=(1,2), right=(3,4)))
front = bot.use(Ultrasonic("front", trigger=5, echo=6))
side  = bot.use(Ultrasonic("side",  trigger=7, echo=8))
@bot.loop
def main():
    if front.distance < 20:
        bot.stop()
    else:
        bot.forward(speed=80)
"""
    prog = parse(src)
    ultrasonics = [c for c in prog.components if c.kind == "Ultrasonic"]
    assert len(ultrasonics) == 2
    names = {c.name for c in ultrasonics}
    assert names == {"front", "side"}


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_error_no_bot():
    with pytest.raises(ParseError):
        parse("from botforge import Bot\n\ndef main(): pass\n")

def test_error_no_loop():
    with pytest.raises(ParseError, match="bot.loop"):
        parse("from botforge import Bot\nbot = Bot('x')\n")

def test_error_unknown_action():
    src = """\
from botforge import Bot, Wheels
bot = Bot("r")
bot.use(Wheels(left=(1,2), right=(3,4)))
@bot.loop
def main():
    bot.fly(speed=100)
"""
    with pytest.raises(Exception, match="fly"):
        parse(src)


# ---------------------------------------------------------------------------
# Integration: example files
# ---------------------------------------------------------------------------

def test_parse_obstacle_example():
    prog = parse_file(EXAMPLES / "obstacle_avoidance.py")
    assert prog.name == "mini_rover"
    assert prog.loop is not None

def test_parse_advanced_example():
    prog = parse_file(EXAMPLES / "advanced_rover.py")
    assert prog.name == "advanced_rover"
    stmt = prog.loop.statements[0]
    assert isinstance(stmt, VarAssign)          # dist = front.distance
    assert len(prog.loop.statements[1].elif_branches) >= 1  # elif
