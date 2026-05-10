"""Tests for botforge.generator"""

import tempfile
from pathlib import Path
import pytest

from botforge.generator import generate
from botforge.ir import (
    ActionCall, BoolCondition, BotProgram, Condition,
    HardwareComponent, IfStatement, LoopFunction,
    SensorRead, VarAssign,
)


def obstacle_program() -> BotProgram:
    wheels = HardwareComponent("wheels", "Wheels", {"left": (5, 6), "right": (9, 10)}, "custom")
    front  = HardwareComponent("front",  "Ultrasonic", {"trigger": 7, "echo": 8}, "NewPing.h")
    loop = LoopFunction([
        IfStatement(
            condition=Condition(
                left=SensorRead("front", "distance"),
                operator="<",
                right=20,
            ),
            then_body=[ActionCall("bot", "turn_left", {"speed": 50})],
            elif_branches=[],
            else_body=[ActionCall("bot", "forward",   {"speed": 80})],
        )
    ])
    return BotProgram("mini_rover", "arduino", [wheels, front], loop)


def get_cpp(program: BotProgram | None = None) -> str:
    prog = program or obstacle_program()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / prog.name
        generate(prog, out)
        return (out / "main.cpp").read_text()


# --- Includes ---

def test_includes_arduino_h():
    assert "#include <Arduino.h>" in get_cpp()

def test_includes_newping_h():
    assert "#include <NewPing.h>" in get_cpp()

def test_no_servo_h_without_servo():
    assert "#include <Servo.h>" not in get_cpp()

# --- normalizeSpeed ---

def test_has_normalize_speed():
    assert "normalizeSpeed" in get_cpp()

def test_normalize_speed_formula():
    cpp = get_cpp()
    assert "(pct * 255) / 100" in cpp or "(speed * 255) / 100" in cpp or "255" in cpp

def test_forward_uses_normalize():
    cpp = get_cpp()
    assert "normalizeSpeed(80)" in cpp

def test_turn_left_uses_normalize():
    cpp = get_cpp()
    assert "normalizeSpeed(50)" in cpp

# --- Entry points ---

def test_has_void_setup():
    assert "void setup()" in get_cpp()

def test_has_void_loop():
    assert "void loop()" in get_cpp()

# --- Sensor code ---

def test_declares_newping():
    assert "NewPing front(" in get_cpp()

def test_uses_ping_cm():
    assert "front.ping_cm()" in get_cpp()

# --- Control flow ---

def test_has_if():
    assert "if (" in get_cpp()

def test_condition_threshold():
    assert "< 20" in get_cpp()

# --- Wheels ---

def test_wheels_forward():
    assert "wheels.forward(" in get_cpp()

def test_wheels_turn_left():
    assert "wheels.turnLeft(" in get_cpp()

# --- elif ---

def test_elif_generated():
    wheels = HardwareComponent("wheels", "Wheels", {"left": (5, 6), "right": (9, 10)}, "custom")
    front  = HardwareComponent("front", "Ultrasonic", {"trigger": 7, "echo": 8}, "NewPing.h")
    loop = LoopFunction([
        IfStatement(
            condition=Condition(SensorRead("front", "distance"), "<", 10),
            then_body=[ActionCall("bot", "stop", {})],
            elif_branches=[(
                Condition(SensorRead("front", "distance"), "<", 30),
                [ActionCall("bot", "turn_left", {"speed": 40})],
            )],
            else_body=[ActionCall("bot", "forward", {"speed": 80})],
        )
    ])
    prog = BotProgram("r", "arduino", [wheels, front], loop)
    assert "} else if (" in get_cpp(prog)

# --- Compound condition ---

def test_bool_condition_and():
    wheels = HardwareComponent("wheels", "Wheels", {"left": (5, 6), "right": (9, 10)}, "custom")
    front  = HardwareComponent("front", "Ultrasonic", {"trigger": 7, "echo": 8}, "NewPing.h")
    loop = LoopFunction([
        IfStatement(
            condition=BoolCondition(
                left=Condition(SensorRead("front", "distance"), "<", 30),
                operator="and",
                right=Condition(SensorRead("front", "distance"), ">", 5),
            ),
            then_body=[ActionCall("bot", "forward", {"speed": 60})],
            elif_branches=[],
            else_body=[],
        )
    ])
    prog = BotProgram("r", "arduino", [wheels, front], loop)
    cpp = get_cpp(prog)
    assert "&&" in cpp

# --- VarAssign ---

def test_var_assign_generates_int():
    wheels = HardwareComponent("wheels", "Wheels", {"left": (5, 6), "right": (9, 10)}, "custom")
    front  = HardwareComponent("front", "Ultrasonic", {"trigger": 7, "echo": 8}, "NewPing.h")
    loop = LoopFunction([
        VarAssign("dist", SensorRead("front", "distance")),
        IfStatement(
            condition=Condition(SensorRead("front", "distance"), "<", 20),
            then_body=[ActionCall("bot", "stop", {})],
            elif_branches=[],
            else_body=[],
        )
    ])
    prog = BotProgram("r", "arduino", [wheels, front], loop)
    cpp = get_cpp(prog)
    assert "int dist = front.ping_cm();" in cpp

# --- Servo ---

def test_servo_includes_servo_h():
    servo = HardwareComponent("arm", "Servo", {"pin": 3}, "Servo.h")
    prog  = BotProgram("sb", "arduino", [servo], LoopFunction([]))
    assert "#include <Servo.h>" in get_cpp(prog)

def test_servo_attach_in_setup():
    servo = HardwareComponent("arm", "Servo", {"pin": 3}, "Servo.h")
    prog  = BotProgram("sb", "arduino", [servo], LoopFunction([]))
    assert "arm.attach(3)" in get_cpp(prog)

# --- Output files ---

def test_creates_readme():
    prog = obstacle_program()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / prog.name
        generate(prog, out)
        assert (out / "README_GENERATED.md").exists()
