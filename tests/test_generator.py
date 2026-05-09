"""Tests for botforge.generator — C++ code generation."""

import tempfile
from pathlib import Path

import pytest

from botforge.generator import generate
from botforge.ir import (
    ActionCall,
    BotProgram,
    Condition,
    HardwareComponent,
    IfStatement,
    LoopFunction,
)


def make_obstacle_program() -> BotProgram:
    """Build the canonical obstacle avoidance IR."""
    wheels = HardwareComponent(
        name="wheels",
        type="Wheels",
        pins={"left": (5, 6), "right": (9, 10)},
        library="custom",
    )
    front = HardwareComponent(
        name="front",
        type="Ultrasonic",
        pins={"trigger": 7, "echo": 8},
        library="NewPing.h",
    )
    loop = LoopFunction(statements=[
        IfStatement(
            condition=Condition(left="front.distance", operator="<", right="20"),
            then_body=[ActionCall(target="bot", method="turn_left", args={"speed": 50})],
            else_body=[ActionCall(target="bot", method="forward", args={"speed": 80})],
        )
    ])
    return BotProgram(
        name="mini_rover",
        target="arduino",
        components=[wheels, front],
        loop=loop,
    )


def generated_cpp(program: BotProgram | None = None) -> str:
    """Run the generator and return the produced main.cpp contents."""
    prog = program or make_obstacle_program()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / prog.name
        generate(prog, out)
        return (out / "main.cpp").read_text()


# ---------------------------------------------------------------------------
# Include directives
# ---------------------------------------------------------------------------

def test_generator_includes_arduino_h():
    cpp = generated_cpp()
    assert "#include <Arduino.h>" in cpp


def test_generator_includes_newping_h():
    cpp = generated_cpp()
    assert "#include <NewPing.h>" in cpp


def test_generator_no_servo_h_when_no_servo():
    cpp = generated_cpp()
    assert "#include <Servo.h>" not in cpp


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def test_generator_has_void_setup():
    cpp = generated_cpp()
    assert "void setup()" in cpp


def test_generator_has_void_loop():
    cpp = generated_cpp()
    assert "void loop()" in cpp


# ---------------------------------------------------------------------------
# Sensor code
# ---------------------------------------------------------------------------

def test_generator_uses_ping_cm():
    cpp = generated_cpp()
    assert "front.ping_cm()" in cpp


def test_generator_declares_newping_instance():
    cpp = generated_cpp()
    assert "NewPing front(" in cpp


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------

def test_generator_has_if():
    cpp = generated_cpp()
    assert "if (" in cpp


def test_generator_condition_with_threshold():
    cpp = generated_cpp()
    assert "< 20" in cpp


# ---------------------------------------------------------------------------
# Movement actions
# ---------------------------------------------------------------------------

def test_generator_wheels_forward():
    cpp = generated_cpp()
    assert "wheels.forward(80)" in cpp


def test_generator_wheels_turn_left():
    cpp = generated_cpp()
    assert "wheels.turnLeft(50)" in cpp


# ---------------------------------------------------------------------------
# Output files
# ---------------------------------------------------------------------------

def test_generator_creates_readme():
    prog = make_obstacle_program()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / prog.name
        generate(prog, out)
        readme = out / "README_GENERATED.md"
        assert readme.exists()
        assert "mini_rover" in readme.read_text().lower() or "Mini Rover" in readme.read_text()


# ---------------------------------------------------------------------------
# Servo target
# ---------------------------------------------------------------------------

def test_generator_includes_servo_h_when_servo_present():
    servo = HardwareComponent(
        name="arm",
        type="Servo",
        pins={"pin": 3},
        library="Servo.h",
    )
    prog = BotProgram(
        name="servo_bot",
        target="arduino",
        components=[servo],
        loop=LoopFunction(statements=[]),
    )
    cpp = generated_cpp(prog)
    assert "#include <Servo.h>" in cpp


def test_generator_attaches_servo_in_setup():
    servo = HardwareComponent(
        name="arm",
        type="Servo",
        pins={"pin": 3},
        library="Servo.h",
    )
    prog = BotProgram(
        name="servo_bot",
        target="arduino",
        components=[servo],
        loop=LoopFunction(statements=[]),
    )
    cpp = generated_cpp(prog)
    assert "arm.attach(3)" in cpp
